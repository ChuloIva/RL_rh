"""Head-to-head video model bake-off on a real shot.

Animates t01_s1 (using its actual keyframe + motion/audio hints) on three
models in parallel so we can A/B/C compare:

  - fal-ai/veo3.1/fast/image-to-video           ($0.15/s w/ audio @ 720p)
  - fal-ai/bytedance/seedance/v1.5/pro/image-to-video  ($0.052/s @ 720p)
  - fal-ai/kling-video/v3/pro/image-to-video    ($0.168/s w/ audio)

Total cost for one 6s clip x 3 models ≈ $2.20.

    python -m video.sample_animate [--shot t01_s1] [--duration 6]
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


SESSION_ID = "paperscarecrow_Gemma-4-31B-it-abliterated_active_imagination_20260527_095319"


def _load_shot(shot_id: str) -> tuple[dict, dict | None, Path, Path | None]:
    """Return (shot, next_shot, keyframe_path, next_keyframe_path?)."""
    turns_dir = config.session_out_dir(SESSION_ID) / "turns"
    flat: list[tuple[Path, dict]] = []
    for td in sorted(turns_dir.iterdir()):
        ext = td / "extraction.json"
        if not ext.exists():
            continue
        data = json.loads(ext.read_text())
        for s in data.get("shots", []):
            flat.append((td, s))

    idx = next(i for i, (_, s) in enumerate(flat) if s["id"] == shot_id)
    td, shot = flat[idx]
    nxt = flat[idx + 1] if idx + 1 < len(flat) else None

    kf = td / "shots" / f"{shot['id']}.png"
    nkf = nxt[0] / "shots" / f"{nxt[1]['id']}.png" if nxt else None
    if nkf and not nkf.exists():
        nkf = None
    return shot, (nxt[1] if nxt else None), kf, nkf


def _motion_prompt(shot: dict) -> str:
    motion = (shot.get("motion_hint") or "").strip()
    ambient = (shot.get("ambient_audio_hint") or "").strip()
    parts = [motion]
    if ambient:
        parts.append(f"Ambient audio: {ambient}.")
    return " ".join(p for p in parts if p)


def _build_jobs(shot: dict, image_url: str, end_image_url: str | None,
                duration: int) -> list[dict]:
    prompt = _motion_prompt(shot)
    print(f"[bake] prompt: {prompt}")

    jobs = [
        {
            "label": "veo31fast",
            "model": "fal-ai/veo3.1/fast/image-to-video",
            "arguments": {
                "prompt": prompt,
                "image_url": image_url,
                "aspect_ratio": "16:9",
                "duration": f"{duration}s",
                "resolution": "720p",
                "generate_audio": True,
            },
        },
        {
            "label": "seedance15pro",
            "model": "fal-ai/bytedance/seedance/v1.5/pro/image-to-video",
            "arguments": {
                "prompt": prompt,
                "image_url": image_url,
                "aspect_ratio": "16:9",
                "duration": str(duration),
                "resolution": "720p",
                "generate_audio": True,
                **({"end_image_url": end_image_url} if end_image_url else {}),
            },
        },
        {
            "label": "kling3pro",
            "model": "fal-ai/kling-video/v3/pro/image-to-video",
            "arguments": {
                "prompt": prompt,
                "start_image_url": image_url,
                "duration": str(duration),
                "generate_audio": True,
                **({"end_image_url": end_image_url} if end_image_url else {}),
            },
        },
    ]
    return jobs


async def _main(shot_id: str, duration: int, out_dir: Path) -> None:
    shot, _nxt, kf, nkf = _load_shot(shot_id)
    if not kf.exists():
        raise RuntimeError(f"keyframe missing: {kf}")
    print(f"[bake] shot={shot_id}  duration={duration}s  end_frame={'yes' if nkf else 'no'}")
    print(f"[bake] keyframe: {kf}")

    print("[bake] uploading keyframes...")
    upload_paths = [kf] + ([nkf] if nkf else [])
    urls = await fal_helpers.aupload_many(upload_paths)
    image_url = urls[0]
    end_url = urls[1] if nkf else None

    jobs = _build_jobs(shot, image_url, end_url, duration)
    out_dir.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    results = await fal_helpers.arun_many(jobs, concurrency=len(jobs))
    print(f"[bake] all done in {time.time()-t0:.1f}s")

    for job, res in zip(jobs, results):
        url = res["video"]["url"]
        dst = out_dir / f"{shot_id}__{job['label']}.mp4"
        fal_helpers.download(url, dst)
        print(f"  -> {dst}")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--shot", default="t01_s1")
    p.add_argument("--duration", type=int, default=6)
    p.add_argument("--out", default=str(Path(__file__).parent / "samples" / "animate"))
    args = p.parse_args()
    asyncio.run(_main(args.shot, args.duration, Path(args.out)))


if __name__ == "__main__":
    main()
