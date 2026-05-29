"""Stage 2 — Style anchor + per-shot keyframes via fal flux (concurrent).

- Generates a single style anchor (flux-pro) at session start from the first
  few shots' image_prompts. Sequential.
- Generates a keyframe per shot using flux/schnell, fanned out concurrently
  with a semaphore.

Idempotent: skips shots whose keyframe PNG already exists.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from video import config, fal_helpers, manifest as mf


STYLE_SUFFIX = (
    " — painterly cinematic still, muted palette, long-take composition, "
    "contemplative stillness in the lineage of Tarkovsky and Sokurov, "
    "no on-screen text, no captions, soft natural lighting."
)

KEYFRAME_CONCURRENCY = 8


def _collect_shots(session_id: str) -> list[dict]:
    turns_dir = config.session_out_dir(session_id) / "turns"
    shots: list[dict] = []
    if not turns_dir.exists():
        return shots
    for turn_dir in sorted(turns_dir.iterdir()):
        ext_path = turn_dir / "extraction.json"
        if not ext_path.exists():
            continue
        data = json.loads(ext_path.read_text())
        for s in data.get("shots", []):
            shots.append({
                "id": s["id"],
                "turn": data["turn"],
                "image_prompt": s.get("image_prompt", ""),
                "turn_dir": turn_dir,
            })
    return shots


def _anchor_prompt(shots: list[dict]) -> str:
    seeds = " | ".join(s["image_prompt"] for s in shots[:3])
    return (
        "Establishing style frame for a short film series. Capture the visual "
        "register that will apply to every shot. Themes from the opening scenes: "
        f"{seeds}. {STYLE_SUFFIX}"
    )


def _ensure_anchor(session_id: str, shots: list[dict],
                   manifest: dict) -> Path:
    anchor_path = config.session_out_dir(session_id) / "style_anchor.png"
    if anchor_path.exists():
        return anchor_path

    print(f"[keyframes] generating style anchor ({config.FAL_ANCHOR_MODEL})")
    result = fal_helpers.run_with_retry(
        config.FAL_ANCHOR_MODEL,
        {
            "prompt": _anchor_prompt(shots),
            "num_images": 1,
            "aspect_ratio": config.FAL_KEYFRAME_ASPECT_RATIO,
            "resolution": config.FAL_KEYFRAME_RESOLUTION,
        },
    )
    url = result["images"][0]["url"]
    fal_helpers.download(url, anchor_path)
    manifest["style_anchor"] = str(anchor_path)
    mf.save(session_id, manifest)
    return anchor_path


def _keyframe_path(shot: dict) -> Path:
    out_dir = shot["turn_dir"] / "shots"
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir / f"{shot['id']}.png"


def _build_job(shot: dict) -> dict:
    prompt = shot["image_prompt"].strip() + STYLE_SUFFIX
    return {
        "model": config.FAL_KEYFRAME_MODEL,
        "arguments": {
            "prompt": prompt,
            "num_images": 1,
            "aspect_ratio": config.FAL_KEYFRAME_ASPECT_RATIO,
            "resolution": config.FAL_KEYFRAME_RESOLUTION,
        },
        "label": shot["id"],
    }


async def _run_concurrent(
    shots_to_make: list[dict],
    session_id: str,
    manifest: dict,
    shots_done: list[str],
) -> None:
    jobs = [_build_job(s) for s in shots_to_make]

    def on_done(idx: int, result: dict) -> None:
        shot = shots_to_make[idx]
        url = result["images"][0]["url"]
        dst = _keyframe_path(shot)
        fal_helpers.download(url, dst)
        manifest["shots"][shot["id"]]["keyframe"] = str(dst)
        if shot["id"] not in shots_done:
            shots_done.append(shot["id"])
        manifest["stages"]["keyframes"]["shots_done"] = shots_done
        mf.save(session_id, manifest)

    await fal_helpers.arun_many(
        jobs, concurrency=KEYFRAME_CONCURRENCY, on_done=on_done,
    )


def keyframes(source_path: str) -> dict:
    session_id = mf.session_id_from(source_path)
    manifest = mf.load_or_init(session_id, source_path)

    if manifest["stages"]["extract"]["status"] != "done":
        raise RuntimeError("run stage 1 (extract) first")

    if manifest["stages"]["keyframes"]["status"] == "done":
        print(f"[keyframes] already done for {session_id}")
        return manifest

    shots = _collect_shots(session_id)
    if not shots:
        raise RuntimeError("no shots found")

    _ensure_anchor(session_id, shots, manifest)

    shots_done: list[str] = manifest["stages"]["keyframes"].get("shots_done", [])

    # Skip shots whose keyframe already exists on disk.
    todo: list[dict] = []
    for shot in shots:
        kf = _keyframe_path(shot)
        if kf.exists():
            manifest["shots"][shot["id"]]["keyframe"] = str(kf)
            if shot["id"] not in shots_done:
                shots_done.append(shot["id"])
            continue
        todo.append(shot)

    mf.save(session_id, {**manifest,
                         "stages": {**manifest["stages"],
                                    "keyframes": {**manifest["stages"]["keyframes"],
                                                  "shots_done": shots_done}}})

    if todo:
        print(f"[keyframes] {len(todo)} shots to generate (concurrency={KEYFRAME_CONCURRENCY})")
        asyncio.run(_run_concurrent(todo, session_id, manifest, shots_done))

    manifest["stages"]["keyframes"]["status"] = "done"
    manifest["stages"]["keyframes"]["shots_done"] = shots_done
    mf.save(session_id, manifest)
    print(f"[keyframes] done. {len(shots_done)} shots.")
    return manifest


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("source")
    args = p.parse_args()
    keyframes(args.source)


if __name__ == "__main__":
    main()
