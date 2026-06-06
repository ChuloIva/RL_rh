"""Head-to-head video bake-off across a whole turn.

For every shot of a target turn (default t01, 5 shots), animates with:
  - fal-ai/veo3.1/fast/image-to-video           (~$0.15/s)
  - fal-ai/bytedance/seedance/v1.5/pro/image-to-video  (~$0.052/s)
  - fal-ai/kling-video/v3/pro/image-to-video    (~$0.168/s)

Then burns subtitles + concatenates each model's shots into a single .mp4
so you can play three full takes side-by-side and pick a winner.

Idempotent: per-model per-shot mp4s that already exist are reused.

    python -m video.sample_animate_turn [--turn t01]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from video import config, fal_helpers
from video.stages import assemble as st_assemble


SESSION_ID = "paperscarecrow_Gemma-4-31B-it-abliterated_active_imagination_20260527_095319"

MODELS: dict[str, dict] = {
    "veo31fast": {
        "model_id": "fal-ai/veo3.1/fast/image-to-video",
        "supports_end_frame": False,
    },
    "seedance15pro": {
        "model_id": "fal-ai/bytedance/seedance/v1.5/pro/image-to-video",
        "supports_end_frame": True,
    },
    "kling3pro": {
        "model_id": "fal-ai/kling-video/v3/pro/image-to-video",
        "supports_end_frame": True,
    },
    "ltx23": {
        "model_id": "fal-ai/ltx-2.3/image-to-video",
        "supports_end_frame": True,
    },
}


def _clamp_veo_duration(d: int) -> int:
    # Veo 3.1 Fast only allows 4s, 6s, 8s — round down to nearest.
    for choice in (8, 6, 4):
        if d >= choice:
            return choice
    return 4


def _clamp_ltx_duration(d: int) -> int:
    # LTX-2.3 duration enum is 6, 8, 10 only — round down to nearest.
    for choice in (10, 8, 6):
        if d >= choice:
            return choice
    return 6


def _args_for(label: str, *, image_url: str, end_url: str | None,
              prompt: str, duration: int) -> dict:
    if label == "veo31fast":
        return {
            "prompt": prompt,
            "image_url": image_url,
            "aspect_ratio": "16:9",
            "duration": f"{_clamp_veo_duration(duration)}s",
            "resolution": "720p",
            "generate_audio": True,
        }
    if label == "seedance15pro":
        d = {
            "prompt": prompt,
            "image_url": image_url,
            "aspect_ratio": "16:9",
            "duration": str(duration),
            "resolution": "720p",
            "generate_audio": True,
        }
        if end_url:
            d["end_image_url"] = end_url
        return d
    if label == "kling3pro":
        d = {
            "prompt": prompt,
            "start_image_url": image_url,
            "duration": str(duration),
            "generate_audio": True,
        }
        if end_url:
            d["end_image_url"] = end_url
        return d
    if label == "ltx23":
        d = {
            "prompt": prompt,
            "image_url": image_url,
            "aspect_ratio": "16:9",
            "duration": _clamp_ltx_duration(duration),  # int enum: 6/8/10
            "resolution": "1080p",
            "fps": 25,  # int enum: 24/25/48/50
            "generate_audio": True,
        }
        if end_url:
            d["end_image_url"] = end_url
        return d
    raise KeyError(label)


def _load_turn(turn: str) -> list[dict]:
    ext = config.session_out_dir(SESSION_ID) / "turns" / turn / "extraction.json"
    data = json.loads(ext.read_text())
    out = []
    for s in data["shots"]:
        kf = config.session_out_dir(SESSION_ID) / "turns" / turn / "shots" / f"{s['id']}.png"
        if not kf.exists():
            raise RuntimeError(f"missing keyframe: {kf}")
        out.append({
            "id": s["id"],
            "prompt": _motion_prompt(s),
            "duration": int(s.get("duration_sec", config.DEFAULT_SHOT_DURATION)),
            "subtitle": s.get("subtitle", ""),
            "keyframe": kf,
        })
    return out


def _motion_prompt(shot: dict) -> str:
    motion = (shot.get("motion_hint") or "").strip()
    ambient = (shot.get("ambient_audio_hint") or "").strip()
    parts = [motion]
    if ambient:
        parts.append(f"Ambient audio: {ambient}.")
    return " ".join(p for p in parts if p)


def _seed_from_first_sample(label: str, out_dir: Path, shot_id: str) -> None:
    """Copy an existing samples/animate/t01_s1__{label}.mp4 into the new layout."""
    legacy = Path(__file__).parent / "samples" / "animate" / f"{shot_id}__{label}.mp4"
    new = out_dir / label / f"{shot_id}.mp4"
    if legacy.exists() and not new.exists():
        new.parent.mkdir(parents=True, exist_ok=True)
        new.write_bytes(legacy.read_bytes())
        print(f"[bake] reused {legacy.name} -> {new.relative_to(out_dir.parent)}")


async def _animate_all(shots: list[dict], out_dir: Path) -> None:
    """Animate every (shot, model) combo whose MP4 isn't already on disk."""
    # Upload every keyframe once.
    paths = [s["keyframe"] for s in shots]
    print(f"[bake] uploading {len(paths)} keyframes...")
    urls = await fal_helpers.aupload_many(paths)
    url_by_id = {s["id"]: u for s, u in zip(shots, urls)}

    jobs: list[dict] = []
    targets: list[tuple[str, str, Path]] = []  # (label, shot_id, dst)

    for i, s in enumerate(shots):
        end_url = url_by_id[shots[i + 1]["id"]] if i + 1 < len(shots) else None
        for label, meta in MODELS.items():
            dst = out_dir / label / f"{s['id']}.mp4"
            if dst.exists():
                print(f"[bake] skip (exists): {dst.relative_to(out_dir.parent)}")
                continue
            args = _args_for(
                label,
                image_url=url_by_id[s["id"]],
                end_url=end_url if meta["supports_end_frame"] else None,
                prompt=s["prompt"],
                duration=s["duration"],
            )
            jobs.append({
                "model": meta["model_id"],
                "arguments": args,
                "label": f"{label}/{s['id']}",
            })
            targets.append((label, s["id"], dst))

    if not jobs:
        print("[bake] nothing to animate — all mp4s already on disk")
        return

    print(f"[bake] {len(jobs)} jobs in flight (concurrency={len(jobs)})")

    def on_done(idx: int, res: dict) -> None:
        label, sid, dst = targets[idx]
        url = res["video"]["url"]
        dst.parent.mkdir(parents=True, exist_ok=True)
        fal_helpers.download(url, dst)
        print(f"  -> {dst.relative_to(out_dir.parent)}")

    t0 = time.time()
    try:
        await fal_helpers.arun_many(jobs, concurrency=len(jobs), on_done=on_done)
    except Exception as e:  # noqa: BLE001
        print(f"[bake] !! some jobs failed: {e}")
        print("[bake] saved partial results are still on disk; re-run to fill gaps")
    print(f"[bake] all done in {time.time()-t0:.1f}s")


def _assemble_per_model(shots: list[dict], out_dir: Path, turn: str) -> dict[str, Path]:
    """For each model: burn subs on each shot, concat into one mp4."""
    finals: dict[str, Path] = {}
    for label in MODELS:
        model_dir = out_dir / label
        subbed_paths: list[Path] = []
        for s in shots:
            src = model_dir / f"{s['id']}.mp4"
            if not src.exists():
                print(f"[bake] !! missing {src}, skipping model {label}")
                subbed_paths = []
                break
            subbed = model_dir / f"{s['id']}.subbed.mp4"
            st_assemble._burn_subtitle(src, subbed, s["subtitle"])
            subbed_paths.append(subbed)
        if not subbed_paths:
            continue
        final = out_dir / f"{turn}__{label}.mp4"
        st_assemble._concat_with_xfade(subbed_paths, final)
        finals[label] = final
        print(f"[bake] {label} -> {final.name}")
    return finals


async def _main(turn: str, out_dir: Path) -> None:
    shots = _load_turn(turn)
    print(f"[bake] turn={turn}  shots={len(shots)}  durations={[s['duration'] for s in shots]}")

    out_dir.mkdir(parents=True, exist_ok=True)
    # Reuse the existing t01_s1 single-shot bake samples if they're there.
    if turn == "t01":
        for label in MODELS:
            _seed_from_first_sample(label, out_dir, "t01_s1")

    await _animate_all(shots, out_dir)
    finals = _assemble_per_model(shots, out_dir, turn)

    print("\n[bake] --- DONE ---")
    for label, p in finals.items():
        size = p.stat().st_size / (1024 * 1024)
        print(f"  {label:>14s}  {p}  ({size:.1f} MB)")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--turn", default="t01")
    p.add_argument(
        "--out",
        default=str(Path(__file__).parent / "samples" / "animate" / "turn01"),
    )
    args = p.parse_args()
    asyncio.run(_main(args.turn, Path(args.out)))


if __name__ == "__main__":
    main()
