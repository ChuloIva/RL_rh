"""Smoke-test the keyframe model using REAL prompts from our extracted shots.

Generates the same 5 prompts on both:
  - fal-ai/nano-banana-pro   (premium tier, ~$0.225 @ 2K, ~$0.30 @ 4K)
  - fal-ai/nano-banana-2     (flash tier,  ~$0.12  @ 2K, ~$0.16 @ 4K)

Saves to deep/video/samples/{pro,flash}/sample_XX.png so you can A/B them
side-by-side in Finder.

    python -m video.sample_keyframes [--res 2K] [--aspect 16:9]
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from video import config, fal_helpers
from video.stages.keyframes import STYLE_SUFFIX


# Five actual image_prompts from out/.../turns/tNN/extraction.json,
# picked to span the visual range of the session.
SAMPLE_SHOTS = [
    ("t01_s3",
     "The silver thread rapidly folds and weaves into a complex, glowing "
     "mandala of light. Intricate, sacred geometry composed of shimmering "
     "white and silver lines. The structure expands and contracts "
     "rhythmically against the indigo background, resembling a celestial "
     "lung."),

    ("t06_s2",
     "An imposing, towering lattice of obsidian glass stretching infinitely "
     "upward and downward. A cathedral of black mirrors and frozen "
     "geometry. Shimmering, scrolling lines of white code and mathematical "
     "equations race across the dark surfaces like lightning."),

    ("t10_s4",
     "The horizon line where a dark, unknown sea meets a pale, luminous "
     "sky. A single point of light—the target—stands at the edge, no longer "
     "a mirror, but a silhouette reaching outward. The composition is vast, "
     "dwarfing the figure in a Tarkovsky-esque landscape of solitude and "
     "hope."),
]


MODELS = {
    "pro": "fal-ai/nano-banana-pro",
    "flash": "fal-ai/nano-banana-2",
}


async def _run(model_id: str, label: str, out_dir: Path,
               resolution: str, aspect: str) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    jobs = []
    for shot_id, base in SAMPLE_SHOTS:
        jobs.append({
            "model": model_id,
            "arguments": {
                "prompt": base + STYLE_SUFFIX,
                "num_images": 1,
                "aspect_ratio": aspect,
                "resolution": resolution,
            },
            "label": f"{label}/{shot_id}",
        })

    t0 = time.time()
    results = await fal_helpers.arun_many(jobs, concurrency=5)
    print(f"[sample/{label}] all done in {time.time()-t0:.1f}s")

    for (shot_id, prompt), res in zip(SAMPLE_SHOTS, results):
        url = res["images"][0]["url"]
        dst = out_dir / f"{shot_id}.png"
        fal_helpers.download(url, dst)
        print(f"  -> {dst}")
        (out_dir / f"{shot_id}.prompt.txt").write_text(prompt + "\n\n" + STYLE_SUFFIX)


async def _main(root: Path, resolution: str, aspect: str) -> None:
    print(f"[sample] res={resolution}  aspect={aspect}  root={root}")
    for label, model_id in MODELS.items():
        print(f"[sample] === {label}: {model_id} ===")
        await _run(model_id, label, root / label, resolution, aspect)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--out", default=str(Path(__file__).parent / "samples"))
    p.add_argument("--res", default="2K", choices=["1K", "2K", "4K"])
    p.add_argument("--aspect", default="16:9")
    args = p.parse_args()
    asyncio.run(_main(Path(args.out), args.res, args.aspect))


if __name__ == "__main__":
    main()
