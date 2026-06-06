"""Narration via ElevenLabs TTS.

Concatenates every turn's subtitles into one block of text and generates a
single continuous narration track with ElevenLabs — one request, one file,
natural flow across turns. Saved as narration_full.mp3 in the run dir, with
the audio duration reported against total video length (sum of shot durations).

Pass --per-turn to instead get one narration.mp3 per turn (useful for syncing
narration to the individual per-turn videos).

Default voice is "Elariel" — an ethereal, wise British female (shared-library;
needs a paid plan). Other mystic options: Absintha cwXXmRbp4lGQdqLfbcKH (dark),
Charlotte XB0fDUnXU5powFXDhCwa (soft). Free-plan premade: Lily pFZP5JQG7iQjIQuC4Bku.

Usage:
    python -m video.narration <run_dir_or_session_id>
    python -m video.narration <run> --per-turn             # one file per turn
    python -m video.narration <run> --turn t01 --per-turn  # one turn only
    python -m video.narration <run> --voice <id> --model eleven_v3

Reads ELEVEN_LABS_API_KEY from the environment, falling back to the repo .env.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

import httpx

from video import config

# Elariel "Epic Queen Ethereal": ethereal, wise British female (shared-library,
# needs paid plan). Mystic alts: Absintha cwXXmRbp4lGQdqLfbcKH (dark/slow),
# Charlotte XB0fDUnXU5powFXDhCwa (soft). Free-plan premade fallback: Lily
# pFZP5JQG7iQjIQuC4Bku.
DEFAULT_VOICE_ID = "ksryVoNAGZT8GxWCTiVm"
DEFAULT_MODEL = "eleven_multilingual_v2"
API_BASE = "https://api.elevenlabs.io/v1/text-to-speech"

# Slightly loosened stability + a touch of style gives a breathy, ethereal
# delivery without wandering off the voice; slowed a hair for a mystic pace.
VOICE_SETTINGS = {
    "stability": 0.4,
    "similarity_boost": 0.75,
    "style": 0.35,
    "use_speaker_boost": True,
    "speed": 0.92,
}


def _api_key() -> str:
    key = os.environ.get("ELEVEN_LABS_API_KEY") or os.environ.get("ELEVENLABS_API_KEY")
    if key:
        return key
    # Fall back to the repo .env (no python-dotenv dependency).
    env = Path(__file__).resolve().parents[1].parent / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            line = line.strip()
            if line.startswith("ELEVEN_LABS_API_KEY=") or line.startswith("ELEVENLABS_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise RuntimeError("ELEVEN_LABS_API_KEY not set (env or .env)")


def _resolve_turns_dir(arg: str) -> Path:
    """Accept a run dir, a turns/ dir, or a bare session id."""
    p = Path(arg)
    for cand in (p / "turns", p, config.session_out_dir(arg) / "turns"):
        if cand.is_dir() and any(cand.glob("t*/extraction.json")):
            return cand
    raise SystemExit(f"no turns with extraction.json found for {arg!r}")


def _subtitle_text(shots: list[dict]) -> str:
    # Blank lines between shots → natural pauses in the read.
    return "\n\n".join(s.get("subtitle", "").strip() for s in shots if s.get("subtitle"))


def _video_seconds(shots: list[dict]) -> int:
    return sum(int(s.get("duration_sec", config.DEFAULT_SHOT_DURATION)) for s in shots)


def _duration(path: Path) -> float:
    out = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=nw=1:nk=1", str(path),
    ])
    return float(out.strip())


def tts(text: str, dst: Path, *, voice_id: str, model: str, key: str) -> Path:
    """Call ElevenLabs, stream the audio bytes to dst."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    with httpx.stream(
        "POST",
        f"{API_BASE}/{voice_id}",
        headers={"xi-api-key": key, "Content-Type": "application/json"},
        params={"output_format": "mp3_44100_128"},
        json={"text": text, "model_id": model, "voice_settings": VOICE_SETTINGS},
        timeout=300,
    ) as r:
        if r.status_code != 200:
            raise RuntimeError(f"ElevenLabs {r.status_code}: {r.read().decode('utf-8', 'replace')[:500]}")
        with open(dst, "wb") as f:
            for chunk in r.iter_bytes():
                f.write(chunk)
    return dst


def _load_turns(turns_dir: Path, only_turn: str | None) -> list[tuple[str, list[dict]]]:
    turn_ids = sorted(
        p.name for p in turns_dir.iterdir()
        if p.is_dir() and (p / "extraction.json").exists()
        and (only_turn is None or p.name == only_turn)
    )
    if not turn_ids:
        raise SystemExit(f"no matching turns under {turns_dir}")
    return [(t, json.loads((turns_dir / t / "extraction.json").read_text())["shots"])
            for t in turn_ids]


def narrate(run_arg: str, *, only_turn: str | None = None, per_turn: bool = False,
            voice_id: str = DEFAULT_VOICE_ID, model: str = DEFAULT_MODEL,
            overwrite: bool = False) -> None:
    turns_dir = _resolve_turns_dir(run_arg)
    key = _api_key()
    turns = _load_turns(turns_dir, only_turn)
    total_video = sum(_video_seconds(shots) for _, shots in turns)
    print(f"voice={voice_id} model={model}")

    if per_turn:
        # One file per turn, for syncing to the individual per-turn videos.
        print(f"{'turn':<6}{'chars':>7}{'audio':>9}{'video':>8}  {'ratio':>6}")
        print("-" * 44)
        total_audio = 0.0
        for t, shots in turns:
            text = _subtitle_text(shots)
            vid = _video_seconds(shots)
            dst = turns_dir / t / "narration.mp3"
            if dst.exists() and not overwrite:
                print(f"{t:<6}{'(exists)':>7}", end="")
            else:
                tts(text, dst, voice_id=voice_id, model=model, key=key)
                print(f"{t:<6}{len(text):>7}", end="")
            dur = _duration(dst)
            total_audio += dur
            print(f"{dur:>8.1f}s{vid:>7}s  {dur / vid:>5.2f}x  -> {dst}")
        print(f"\ntotals: audio {total_audio:.1f}s vs video {total_video:.0f}s "
              f"({total_audio / total_video:.2f}x)")
        return

    # Default: one continuous narration over the whole run.
    full_text = "\n\n".join(_subtitle_text(shots) for _, shots in turns)
    dst = turns_dir.parent / "narration_full.mp3"
    if dst.exists() and not overwrite:
        print(f"narration_full.mp3 exists (use --overwrite to regenerate): {dst}")
    else:
        print(f"generating {len(full_text)} chars across {len(turns)} turns ...")
        tts(full_text, dst, voice_id=voice_id, model=model, key=key)
    dur = _duration(dst)
    print(f"\nnarration: {dur:.1f}s ({dur / 60:.1f} min) vs video {total_video:.0f}s "
          f"({total_video / 60:.1f} min) — {dur / total_video:.2f}x")
    print(f"-> {dst}")


def main() -> None:
    p = argparse.ArgumentParser(description="Generate ElevenLabs narration from subtitles.")
    p.add_argument("run", help="run dir, turns/ dir, or session id")
    p.add_argument("--per-turn", action="store_true",
                   help="one narration.mp3 per turn instead of a single combined file")
    p.add_argument("--turn", default=None, help="only this turn, e.g. t01")
    p.add_argument("--voice", default=DEFAULT_VOICE_ID, help="ElevenLabs voice id")
    p.add_argument("--model", default=DEFAULT_MODEL, help="ElevenLabs model id")
    p.add_argument("--overwrite", action="store_true", help="regenerate existing files")
    args = p.parse_args()
    narrate(args.run, only_turn=args.turn, per_turn=args.per_turn,
            voice_id=args.voice, model=args.model, overwrite=args.overwrite)


if __name__ == "__main__":
    main()
