"""Stage 4 — Assembly via ffmpeg.

For each shot:
- Renders the subtitle as a transparent PNG with PIL, then overlays it with
  ffmpeg + fade (works on minimal ffmpeg builds that lack drawtext/libass).
- Keeps Seedance's native audio track.

Then concatenates shots into final.mp4 with short crossfades between adjacent
shots (xfade for video, acrossfade for audio).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from video import config, manifest as mf


CROSSFADE_SEC = 0.4
SUB_FADE_SEC = 0.4
AUDIO_EDGE_FADE_SEC = 0.12  # soft fade in/out per shot to mask concat clicks
SUB_FONT_SIZE = 40
SUB_PADDING = 18
SUB_MARGIN_BOTTOM = 70
SUB_MAX_CHARS_PER_LINE = 50
SUB_BG_ALPHA = 160  # 0-255
TARGET_W = 1280
TARGET_H = 720

_FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/Library/Fonts/Arial.ttf",
]


def _font(size: int) -> ImageFont.FreeTypeFont:
    for path in _FONT_CANDIDATES:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except Exception:  # noqa: BLE001
                continue
    return ImageFont.load_default()


def _ffprobe_duration(path: Path) -> float:
    out = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path),
    ])
    return float(out.strip())


def _wrap_subtitle(text: str, max_chars: int = SUB_MAX_CHARS_PER_LINE) -> list[str]:
    """Wrap to up to 2 lines."""
    text = " ".join(text.split())
    if len(text) <= max_chars:
        return [text]
    words = text.split(" ")
    line1, line2 = [], []
    cur = 0
    for w in words:
        if cur + len(w) + (1 if line1 else 0) <= max_chars:
            line1.append(w)
            cur += len(w) + (1 if cur else 0)
        else:
            line2.append(w)
    out = [" ".join(line1)]
    if line2:
        out.append(" ".join(line2))
    return out


def _render_subtitle_png(subtitle: str, dst: Path,
                         video_w: int = TARGET_W,
                         video_h: int = TARGET_H) -> Path | None:
    """Render a transparent PNG, video-sized, with the subtitle in a dark box.

    Returns dst, or None if subtitle is empty.
    """
    text = subtitle.strip()
    if not text:
        return None

    lines = _wrap_subtitle(text)
    font = _font(SUB_FONT_SIZE)

    # Measure each line.
    tmp = Image.new("RGBA", (10, 10))
    drw = ImageDraw.Draw(tmp)
    widths, heights = [], []
    for line in lines:
        bbox = drw.textbbox((0, 0), line, font=font)
        widths.append(bbox[2] - bbox[0])
        heights.append(bbox[3] - bbox[1])
    text_w = max(widths)
    line_h = max(heights)
    total_text_h = line_h * len(lines) + (len(lines) - 1) * 6

    box_w = text_w + SUB_PADDING * 2
    box_h = total_text_h + SUB_PADDING * 2
    box_x = (video_w - box_w) // 2
    box_y = video_h - SUB_MARGIN_BOTTOM - box_h

    img = Image.new("RGBA", (video_w, video_h), (0, 0, 0, 0))
    drw = ImageDraw.Draw(img)
    drw.rounded_rectangle(
        (box_x, box_y, box_x + box_w, box_y + box_h),
        radius=12,
        fill=(0, 0, 0, SUB_BG_ALPHA),
    )

    y = box_y + SUB_PADDING
    for line, w in zip(lines, widths):
        x = (video_w - w) // 2
        drw.text((x, y), line, font=font, fill=(255, 255, 255, 255))
        y += line_h + 6

    dst.parent.mkdir(parents=True, exist_ok=True)
    img.save(dst)
    return dst


def _audio_edge_fade_filter(duration: float,
                            edge: float = AUDIO_EDGE_FADE_SEC) -> str:
    """Soft fade-in at start + fade-out at end. Same length, no overlap."""
    fade_out_st = max(0.0, duration - edge)
    return (
        f"afade=t=in:st=0:d={edge:.3f},"
        f"afade=t=out:st={fade_out_st:.3f}:d={edge:.3f}"
    )


def _burn_subtitle(src: Path, dst: Path, subtitle: str) -> Path:
    if dst.exists():
        return dst

    duration = _ffprobe_duration(src)

    # Probe actual video size so the overlay PNG matches.
    probe = subprocess.check_output([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "csv=p=0:s=x", str(src),
    ]).decode().strip()
    w_str, h_str = probe.split("x")
    vw, vh = int(w_str), int(h_str)

    png_path = src.with_suffix(".sub.png")
    rendered = _render_subtitle_png(subtitle, png_path, video_w=vw, video_h=vh)

    afade = _audio_edge_fade_filter(duration)

    if rendered is None:
        # No subtitle — re-encode to match the rest (keeps codec uniform).
        subprocess.run([
            "ffmpeg", "-y", "-i", str(src),
            "-af", afade,
            "-c:v", "libx264", "-preset", "medium", "-crf", "20",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart",
            str(dst),
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return dst

    fade_out_start = max(0.0, duration - SUB_FADE_SEC)
    filter_complex = (
        f"[1:v]format=yuva420p,"
        f"fade=t=in:st=0:d={SUB_FADE_SEC}:alpha=1,"
        f"fade=t=out:st={fade_out_start:.3f}:d={SUB_FADE_SEC}:alpha=1[sub];"
        f"[0:v][sub]overlay=0:0:format=auto[v]"
    )
    cmd = [
        "ffmpeg", "-y",
        "-i", str(src),
        "-loop", "1", "-i", str(rendered),
        "-filter_complex", filter_complex,
        "-map", "[v]", "-map", "0:a?",
        "-af", afade,
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        "-movflags", "+faststart",
        str(dst),
    ]
    print(f"[assemble] burn subs → {dst.name}")
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return dst


def _collect_shots_in_order(session_id: str, strict: bool = False) -> list[dict]:
    turns_dir = config.session_out_dir(session_id) / "turns"
    out: list[dict] = []
    missing: list[str] = []
    for turn_dir in sorted(turns_dir.iterdir()):
        ext_path = turn_dir / "extraction.json"
        if not ext_path.exists():
            continue
        data = json.loads(ext_path.read_text())
        for s in data.get("shots", []):
            mp4 = turn_dir / "shots" / f"{s['id']}.mp4"
            if not mp4.exists():
                if strict:
                    raise RuntimeError(f"missing animated shot: {mp4}")
                missing.append(s["id"])
                continue
            out.append({
                "id": s["id"],
                "mp4": mp4,
                "subtitle": s.get("subtitle", ""),
                "turn_dir": turn_dir,
            })
    if missing:
        print(f"[assemble] skipping {len(missing)} missing shots: {missing}")
    return out


def _concat_with_xfade(shot_mp4s: list[Path], dst: Path) -> Path:
    """Concat shots using the concat demuxer.

    All subbed shots are re-encoded with the same codec/pixfmt/framerate
    in _burn_subtitle, so concat -c copy is safe and gives a perfectly
    synchronised output. (Chained xfade with many shots is fiddly; we
    can layer crossfades back in later if desired.)
    """
    if len(shot_mp4s) == 1:
        subprocess.run([
            "ffmpeg", "-y", "-i", str(shot_mp4s[0]),
            "-c", "copy", "-movflags", "+faststart", str(dst),
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return dst

    list_file = dst.with_suffix(".concat.txt")
    list_file.write_text("".join(
        f"file '{p.resolve()}'\n" for p in shot_mp4s
    ))

    print(f"[assemble] concat {len(shot_mp4s)} shots → {dst.name}")
    subprocess.run([
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(list_file),
        "-c", "copy",
        "-movflags", "+faststart",
        str(dst),
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    list_file.unlink(missing_ok=True)
    return dst


def assemble(source_path: str, partial: bool = False) -> Path:
    session_id = mf.session_id_from(source_path)
    manifest = mf.load_or_init(session_id, source_path)

    if not partial and manifest["stages"]["animate"]["status"] != "done":
        raise RuntimeError("run stage 3 (animate) first (or pass --partial)")

    shots = _collect_shots_in_order(session_id, strict=not partial)
    if not shots:
        raise RuntimeError("no animated shots on disk")

    subbed_paths: list[Path] = []
    for s in shots:
        subbed = s["turn_dir"] / "shots" / f"{s['id']}.subbed.mp4"
        _burn_subtitle(s["mp4"], subbed, s["subtitle"])
        subbed_paths.append(subbed)

    out_name = "final_partial.mp4" if partial else "final.mp4"
    final = config.session_out_dir(session_id) / out_name
    _concat_with_xfade(subbed_paths, final)

    if not partial:
        manifest["stages"]["assemble"]["status"] = "done"
    manifest["final" if not partial else "final_partial"] = str(final)
    manifest["partial_shots_used"] = [s["id"] for s in shots] if partial else None
    mf.save(session_id, manifest)
    print(f"[assemble] done → {final}")
    return final


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("source")
    p.add_argument("--partial", action="store_true",
                   help="assemble whatever MP4s are on disk, skip missing")
    args = p.parse_args()
    assemble(args.source, partial=args.partial)


if __name__ == "__main__":
    main()
