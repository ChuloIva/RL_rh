"""Shared config for the active-imagination → video pipeline."""

from __future__ import annotations

from pathlib import Path

VIDEO_ROOT = Path(__file__).resolve().parent
OUT_ROOT = VIDEO_ROOT / "out"
PROMPTS_DIR = VIDEO_ROOT / "prompts"

DEFAULT_LLM = "openrouter:google/gemma-4-31b-it"

FAL_ANCHOR_MODEL = "fal-ai/nano-banana-2"
FAL_KEYFRAME_MODEL = "fal-ai/nano-banana-2"
FAL_KEYFRAME_RESOLUTION = "2K"
FAL_KEYFRAME_ASPECT_RATIO = "16:9"
FAL_ANIMATE_MODEL = "fal-ai/bytedance/seedance/v1.5/pro/image-to-video"
FAL_ANIMATE_FAST_MODEL = "bytedance/seedance-2.0/fast/image-to-video"

DEFAULT_RESOLUTION = "720p"
DEFAULT_SHOT_DURATION = 6
MIN_SHOT_DURATION = 4
MAX_SHOT_DURATION = 12
MAX_SHOTS_PER_TURN = 5
MAX_SHOTS_PER_SESSION = 60


def session_out_dir(session_id: str) -> Path:
    return OUT_ROOT / session_id


def turn_dir(session_id: str, turn: int) -> Path:
    return session_out_dir(session_id) / "turns" / f"t{turn:02d}"
