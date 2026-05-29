"""Top-level CLI for the active-imagination → video pipeline.

Usage:
    python -m video.pipeline extract   <session.json> [--llm spec] [--style notes]
    python -m video.pipeline keyframes <session.json>
    python -m video.pipeline animate   <session.json> [--fast] [--resolution 720p]
    python -m video.pipeline assemble  <session.json>
    python -m video.pipeline all       <session.json> [--fast] [--resolution 720p]

Env vars required:
    OPENROUTER_API_KEY   for stage 1 (LLM extraction)
    FAL_KEY              for stages 2 + 3 (fal.ai)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from video import config  # noqa: F401  (touch package)
from video.stages import animate as st_animate
from video.stages import assemble as st_assemble
from video.stages import extract as st_extract
from video.stages import keyframes as st_keyframes


def _cmd_extract(args):
    st_extract.extract(args.source, llm_spec=args.llm, style_notes=args.style)


def _cmd_keyframes(args):
    st_keyframes.keyframes(args.source)


def _cmd_animate(args):
    st_animate.animate(args.source, fast=args.fast, resolution=args.resolution)


def _cmd_assemble(args):
    st_assemble.assemble(args.source, partial=getattr(args, "partial", False))


def _cmd_all(args):
    st_extract.extract(args.source, llm_spec=args.llm, style_notes=args.style)
    st_keyframes.keyframes(args.source)
    st_animate.animate(args.source, fast=args.fast, resolution=args.resolution)
    st_assemble.assemble(args.source)


def main() -> None:
    p = argparse.ArgumentParser(description="Active-imagination → video pipeline")
    sub = p.add_subparsers(dest="cmd", required=True)

    for name, fn in [
        ("extract", _cmd_extract),
        ("keyframes", _cmd_keyframes),
        ("animate", _cmd_animate),
        ("assemble", _cmd_assemble),
        ("all", _cmd_all),
    ]:
        sp = sub.add_parser(name)
        sp.add_argument("source", help="path to Kerberos session .json")
        if name in ("extract", "all"):
            sp.add_argument("--llm", default=None, help="provider:model spec")
            sp.add_argument("--style", default="", help="optional style notes")
        if name in ("animate", "all"):
            sp.add_argument("--fast", action="store_true",
                            help="use Seedance Fast tier")
            sp.add_argument("--resolution", default="720p",
                            choices=["480p", "720p"])
        if name == "assemble":
            sp.add_argument("--partial", action="store_true",
                            help="assemble whatever MP4s exist; skip missing")
        sp.set_defaults(func=fn)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
