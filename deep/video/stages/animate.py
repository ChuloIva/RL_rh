"""Stage 3 — Image-to-video via Seedance 2.0 (native audio ON), concurrent.

Per shot:
- Uploads its keyframe (start frame).
- Optionally uploads the next shot's keyframe as end_image_url for free
  continuity transitions.
- Submits to bytedance/seedance-2.0/image-to-video with generate_audio=True.

All shots fanned out concurrently via fal_helpers.arun_many.
Idempotent: skips shots whose MP4 already exists.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from video import config, fal_helpers, manifest as mf


ANIMATE_CONCURRENCY = 6


def _collect_shot_records(session_id: str) -> list[dict]:
    turns_dir = config.session_out_dir(session_id) / "turns"
    out: list[dict] = []
    for turn_dir in sorted(turns_dir.iterdir()):
        ext_path = turn_dir / "extraction.json"
        if not ext_path.exists():
            continue
        data = json.loads(ext_path.read_text())
        for s in data.get("shots", []):
            out.append({
                "id": s["id"],
                "turn": data["turn"],
                "turn_dir": turn_dir,
                "shot": s,
            })
    return out


def _animate_prompt(shot: dict) -> str:
    motion = (shot.get("motion_hint") or "").strip()
    ambient = (shot.get("ambient_audio_hint") or "").strip()
    parts = [motion]
    if ambient:
        parts.append(f"Ambient audio: {ambient}.")
    return " ".join(p for p in parts if p)


def _video_path(record: dict) -> Path:
    return record["turn_dir"] / "shots" / f"{record['id']}.mp4"


def _keyframe_path(record: dict) -> Path:
    return record["turn_dir"] / "shots" / f"{record['id']}.png"


async def _build_jobs(
    records: list[dict],
    todo_indices: list[int],
    fast: bool,
    resolution: str,
) -> list[dict]:
    """Upload keyframes (start + end) concurrently, then build job dicts."""
    # Gather all unique keyframe paths we need to upload.
    needed_paths: list[Path] = []
    path_index: dict[str, int] = {}
    for i in todo_indices:
        kf = _keyframe_path(records[i])
        if str(kf) not in path_index:
            path_index[str(kf)] = len(needed_paths)
            needed_paths.append(kf)
        # end frame from next shot if present
        if i + 1 < len(records):
            nkf = _keyframe_path(records[i + 1])
            if nkf.exists() and str(nkf) not in path_index:
                path_index[str(nkf)] = len(needed_paths)
                needed_paths.append(nkf)

    print(f"[animate] uploading {len(needed_paths)} keyframes...")
    urls = await fal_helpers.aupload_many(needed_paths, concurrency=8)
    url_for = {str(p): u for p, u in zip(needed_paths, urls)}

    model = config.FAL_ANIMATE_FAST_MODEL if fast else config.FAL_ANIMATE_MODEL
    jobs: list[dict] = []
    for i in todo_indices:
        rec = records[i]
        shot = rec["shot"]
        args = {
            "image_url": url_for[str(_keyframe_path(rec))],
            "prompt": _animate_prompt(shot),
            "aspect_ratio": "16:9",
            "duration": str(shot.get("duration_sec", config.DEFAULT_SHOT_DURATION)),
            "resolution": resolution,
            "generate_audio": True,
            "enable_safety_checker": False,  # reduce false-positive content flags
        }
        if i + 1 < len(records):
            nkf = _keyframe_path(records[i + 1])
            if nkf.exists():
                args["end_image_url"] = url_for[str(nkf)]
        jobs.append({"model": model, "arguments": args, "label": rec["id"]})
    return jobs


async def _run_concurrent(
    records: list[dict],
    todo_indices: list[int],
    session_id: str,
    manifest: dict,
    shots_done: list[str],
    fast: bool,
    resolution: str,
) -> None:
    jobs = await _build_jobs(records, todo_indices, fast, resolution)

    def on_done(jdx: int, result: dict) -> None:
        ridx = todo_indices[jdx]
        rec = records[ridx]
        video_url = result["video"]["url"]
        dst = _video_path(rec)
        fal_helpers.download(video_url, dst)
        manifest["shots"][rec["id"]]["video"] = str(dst)
        if rec["id"] not in shots_done:
            shots_done.append(rec["id"])
        manifest["stages"]["animate"]["shots_done"] = shots_done
        mf.save(session_id, manifest)

    print(f"[animate] {len(jobs)} shots in flight (concurrency={ANIMATE_CONCURRENCY})")
    await fal_helpers.arun_many(jobs, concurrency=ANIMATE_CONCURRENCY,
                                on_done=on_done)


def animate(source_path: str, fast: bool = False,
            resolution: str = config.DEFAULT_RESOLUTION) -> dict:
    session_id = mf.session_id_from(source_path)
    manifest = mf.load_or_init(session_id, source_path)

    if manifest["stages"]["keyframes"]["status"] != "done":
        raise RuntimeError("run stage 2 (keyframes) first")

    if manifest["stages"]["animate"]["status"] == "done":
        print(f"[animate] already done for {session_id}")
        return manifest

    records = _collect_shot_records(session_id)
    shots_done: list[str] = manifest["stages"]["animate"].get("shots_done", [])

    # Pick up where we left off: skip shots whose MP4 already exists.
    todo: list[int] = []
    for i, rec in enumerate(records):
        if _video_path(rec).exists():
            manifest["shots"][rec["id"]]["video"] = str(_video_path(rec))
            if rec["id"] not in shots_done:
                shots_done.append(rec["id"])
            continue
        todo.append(i)

    manifest["stages"]["animate"]["shots_done"] = shots_done
    mf.save(session_id, manifest)

    if todo:
        asyncio.run(_run_concurrent(records, todo, session_id, manifest,
                                    shots_done, fast, resolution))

    # Re-scan disk: only mark the stage done when EVERY shot rendered.
    rendered = [rec["id"] for rec in records if _video_path(rec).exists()]
    missing = [rec["id"] for rec in records if not _video_path(rec).exists()]
    manifest["stages"]["animate"]["shots_done"] = rendered
    if missing:
        manifest["stages"]["animate"]["status"] = "incomplete"
        manifest["stages"]["animate"]["missing"] = missing
        print(f"[animate] {len(rendered)}/{len(records)} done. "
              f"{len(missing)} still missing: {missing}")
        print("[animate] re-run to retry missing shots, or assemble --partial.")
    else:
        manifest["stages"]["animate"]["status"] = "done"
        manifest["stages"]["animate"].pop("missing", None)
        print(f"[animate] done. all {len(rendered)} shots rendered.")
    mf.save(session_id, manifest)
    return manifest


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("source")
    p.add_argument("--fast", action="store_true",
                   help="use Seedance Fast tier (cheaper, lower quality)")
    p.add_argument("--resolution", default=config.DEFAULT_RESOLUTION,
                   choices=["480p", "720p"])
    args = p.parse_args()
    animate(args.source, fast=args.fast, resolution=args.resolution)


if __name__ == "__main__":
    main()
