"""Narration via ElevenLabs TTS.

Reads each turn's subtitles from its extraction.json, generates a spoken
narration track with ElevenLabs, saves it next to the turn, and reports the
audio duration against the turn's video length (sum of shot durations).

Default voice is "Charlotte" — a soft, breathy British female voice well
suited to mystic / atmospheric narration. Override with --voice / --model.

Usage:
    python -m video.narration <run_dir_or_session_id>
    python -m video.narration <run> --turn t01            # one turn
    python -m video.narration <run> --no-full              # skip combined file
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

# Charlotte: soft British female, made for meditation / calming narration.
DEFAULT_VOICE_ID = "XB0fDUnXU5powFXDhCwa"
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


def narrate(run_arg: str, *, only_turn: str | None = None, make_full: bool = True,
            voice_id: str = DEFAULT_VOICE_ID, model: str = DEFAULT_MODEL,
            overwrite: bool = False) -> None:
    turns_dir = _resolve_turns_dir(run_arg)
    key = _api_key()

    turn_ids = sorted(
        p.name for p in turns_dir.iterdir()
        if p.is_dir() and (p / "extraction.json").exists()
        and (only_turn is None or p.name == only_turn)
    )
    if not turn_ids:
        raise SystemExit(f"no matching turns under {turns_dir}")

    print(f"voice={voice_id} model={model}")
    print(f"{'turn':<6}{'chars':>7}{'audio':>9}{'video':>8}  {'ratio':>6}")
    print("-" * 40)

    full_parts: list[str] = []
    total_audio = total_video = 0.0
    for t in turn_ids:
        shots = json.loads((turns_dir / t / "extraction.json").read_text())["shots"]
        text = _subtitle_text(shots)
        full_parts.append(text)
        vid = _video_seconds(shots)
        total_video += vid

        dst = turns_dir / t / "narration.mp3"
        if dst.exists() and not overwrite:
            print(f"{t:<6}{'(exists)':>7}", end="")
        else:
            tts(text, dst, voice_id=voice_id, model=model, key=key)
            print(f"{t:<6}{len(text):>7}", end="")
        dur = _duration(dst)
        total_audio += dur
        print(f"{dur:>8.1f}s{vid:>7}s  {dur / vid:>5.2f}x  -> {dst}")

    if make_full and len(turn_ids) > 1:
        full_text = "\n\n".join(full_parts)
        full_dst = turns_dir.parent / "narration_full.mp3"
        if full_dst.exists() and not overwrite:
            print(f"\nfull (exists): {full_dst}")
        else:
            tts(full_text, full_dst, voice_id=voice_id, model=model, key=key)
        fdur = _duration(full_dst)
        print(f"\nfull narration: {fdur:.1f}s ({fdur/60:.1f} min), {len(full_text)} chars -> {full_dst}")

    print(f"\ntotals: audio {total_audio:.1f}s vs video {total_video:.0f}s "
          f"({total_audio/total_video:.2f}x)")


def main() -> None:
    p = argparse.ArgumentParser(description="Generate ElevenLabs narration from subtitles.")
    p.add_argument("run", help="run dir, turns/ dir, or session id")
    p.add_argument("--turn", default=None, help="only this turn, e.g. t01")
    p.add_argument("--no-full", action="store_true", help="skip the combined narration_full.mp3")
    p.add_argument("--voice", default=DEFAULT_VOICE_ID, help="ElevenLabs voice id")
    p.add_argument("--model", default=DEFAULT_MODEL, help="ElevenLabs model id")
    p.add_argument("--overwrite", action="store_true", help="regenerate existing files")
    args = p.parse_args()
    narrate(args.run, only_turn=args.turn, make_full=not args.no_full,
            voice_id=args.voice, model=args.model, overwrite=args.overwrite)


if __name__ == "__main__":
    main()
