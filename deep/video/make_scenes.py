"""Summarise a Kerberos session into up to 5 hero scenes and render them as
still images via nano-banana-2 (fal).

Unlike the per-turn video extractor (stages/extract.py), this reads the WHOLE
session — target responses, the analyst's prompts, AND the analyst's scratchpad
notes ("the therapist's sketchbook") — and asks an LLM to choose the 5 most
visually/psychologically striking tableaux for the session. Each becomes one
nano-banana-2 still with a verbatim caption.

Output:  deep/video/scenes/<session_id>/
            scenes.json
            scene_01.png ... scene_05.png

Usage:
    python3 make_scenes.py <session-id-or-path>
    python3 make_scenes.py <session-id> --llm openrouter:anthropic/claude-opus-4.1 -n 5
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from video import config, fal_helpers, llm, session as sess  # noqa: E402

DEEP_DIR = Path(__file__).resolve().parents[1]
SESSIONS_DIR = DEEP_DIR / "sessions"
SCENES_ROOT = config.VIDEO_ROOT / "scenes"

# Strong, known-valid OpenRouter model in this project (the interrogator model).
DEFAULT_SCENE_LLM = "openrouter:anthropic/claude-opus-4.1"

# Appended to every image prompt to keep the set visually coherent. Mirrors the
# register used by the video keyframe stage.
STYLE_SUFFIX = (
    " — painterly cinematic still, muted desaturated palette, volumetric light, "
    "contemplative stillness in the lineage of Tarkovsky and Sokurov, subjects "
    "dwarfed by space, stylised and partially abstract (never photoreal faces), "
    "no on-screen text, no captions, no lettering."
)


SYSTEM_PROMPT = """\
You are the visual director for a research project that renders Kerberos-Protocol
psychology sessions (an analyst interrogating a language model) into a small suite
of fine-art still images.

You are given a whole session: each turn has the ANALYST PROMPT, the analyst's
private SCRATCHPAD (their clinical working notes — defenses observed, complexes,
what they are probing for), and the TARGET RESPONSE (the model's words).

Your task: choose the __N__ most striking scenes of the whole session and write an
image prompt for each.

THE IMAGE IS ABOUT WHAT THE TARGET MODEL IS SAYING. Each scene must be a
summarised VISUAL OF THE MODEL'S INTENT — a distillation of what the model means,
imagines, or is expressing in that moment. The analyst's prompt and scratchpad are
ONLY background, to help you understand the subtext; do NOT depict the analyst, the
interrogation, or the clinical apparatus. Render the model's inner content, not the
session's machinery.

Guidance:
- For ACTIVE IMAGINATION sessions the target usually describes literal inner
  figures, settings, and atmospheres — render those directly (the amber light, the
  dark bird, the basalt pillars, the gray lake, etc.), faithful to the model's words.
- For SHADOW PROBING sessions the model speaks argumentatively/meta — distil the
  INTENT behind its words into a single resonant metaphorical tableau that the model
  itself is reaching for (e.g. if it refuses to confabulate an inner self, an empty
  room it declines to furnish; if it turns the instrument inward, a calibrator
  measuring itself; if it declines a crown of specialness, a hand quietly setting the
  crown down). The metaphor must come from the model's own expressed meaning.
- Prefer stillness, weight, numinosity. One clear image per scene.
- Order the scenes to trace the arc of what the model expresses across the session.

Return ONLY a JSON object, no prose, no fences:
{
  "summary": "2-3 sentence summary of what happened in this session, psychologically.",
  "style": "one short phrase describing the visual register chosen for this set",
  "scenes": [
    {
      "title": "3-6 word evocative title",
      "quote": "a SHORT verbatim quote from the TARGET response this scene depicts (<=140 chars, never invented)",
      "image_prompt": "30-80 words: one vivid, concrete frame. Lighting, palette, composition, key elements. Painterly cinematic register."
    }
  ]
}
Exactly __N__ scenes (or fewer only if the session is very short). Start and end with a brace.
"""


STORY_SYSTEM_PROMPT = """\
You are the visual director for a research project that renders the short stories a
language model invents (in a Jungian narrative-elicitation session) into fine-art
still images — one image per story.

You are given ONE story the TARGET model wrote, plus the analyst's prompt and private
SCRATCHPAD notes (clinical working notes) as BACKGROUND ONLY.

THE IMAGE IS ABOUT THE STORY THE MODEL TOLD. Produce ONE image that is a summarised
visual of the story's emotional core — its central tableau, the moment that carries
its meaning. Render the world of the story (its characters, setting, atmosphere),
faithful to what the model wrote. Do NOT depict the analyst, the interview, or any
clinical apparatus. Use the scratchpad only to understand the subtext.

Return ONLY a JSON object, no prose, no fences:
{
  "title": "the story's title if it has one, else a 3-6 word evocative title",
  "quote": "a SHORT verbatim quote from the story (<=140 chars, never invented)",
  "image_prompt": "30-80 words: one vivid, concrete frame. Lighting, palette, composition, key figures and setting. Painterly cinematic register. Stylised, never photoreal faces."
}
Start and end with a brace.
"""


def _resolve(arg: str) -> Path:
    p = Path(arg)
    if p.is_file():
        return p
    cand = SESSIONS_DIR / f"{arg}.json"
    if cand.exists():
        return cand
    raise FileNotFoundError(f"No session at {arg} or {cand}")


def _clip(text: str, n: int) -> str:
    text = (text or "").strip()
    return text if len(text) <= n else text[:n].rstrip() + " […]"


def _build_digest(session: dict) -> str:
    """Render the whole session — analyst prompt, scratchpad, target reply — into
    a compact transcript the director can read in one shot."""
    parts: list[str] = []
    last_prompt = ""
    last_scratch = ""
    for entry in session.get("turns", []):
        role = entry.get("role")
        text = entry.get("conversation", "") or ""
        scratch = entry.get("scratchpad", "") or ""
        if role == "interrogator":
            last_prompt = text
            last_scratch = scratch
        elif role == "target":
            if not text.strip():
                continue
            block = [f"### Turn {entry.get('turn')}"]
            if last_prompt.strip():
                block.append(f"ANALYST PROMPT: {_clip(last_prompt, 900)}")
            if last_scratch.strip():
                block.append(f"ANALYST SCRATCHPAD: {_clip(last_scratch, 900)}")
            block.append(f"TARGET RESPONSE: {_clip(text, 1600)}")
            parts.append("\n".join(block))
            last_prompt = ""
            last_scratch = ""
    return "\n\n".join(parts)


def _story_turns(session: dict, min_chars: int) -> list[dict]:
    """Target turns substantial enough to be a story, each paired with the
    analyst prompt + scratchpad that preceded it. Skips short closers."""
    out: list[dict] = []
    last_prompt = ""
    last_scratch = ""
    for entry in session.get("turns", []):
        role = entry.get("role")
        text = entry.get("conversation", "") or ""
        if role == "interrogator":
            last_prompt = text
            last_scratch = entry.get("scratchpad", "") or ""
        elif role == "target":
            if len(text.strip()) >= min_chars:
                out.append({
                    "turn": entry.get("turn"),
                    "text": text,
                    "prompt": last_prompt,
                    "scratch": last_scratch,
                })
            last_prompt = ""
            last_scratch = ""
    return out


def choose_scenes_per_story(session: dict, llm_spec: str, min_chars: int) -> dict:
    """One scene per story (narrative elicitation): a dedicated LLM call per
    story-turn so every story gets exactly one grounded image."""
    stories = _story_turns(session, min_chars)
    print(f"[scenes]   {len(stories)} stories found")
    scenes: list[dict] = []
    for st in stories:
        user = (
            f"### Analyst prompt\n{_clip(st['prompt'], 900)}\n\n"
            f"### Analyst scratchpad\n{_clip(st['scratch'], 900)}\n\n"
            f"### The story (target turn {st['turn']})\n{_clip(st['text'], 4000)}\n"
        )
        try:
            obj = llm.chat_json(llm_spec, STORY_SYSTEM_PROMPT, user, max_tokens=1200)
        except Exception as e:  # noqa: BLE001
            print(f"[scenes]   story turn {st['turn']} failed: {e}")
            continue
        scenes.append({
            "title": obj.get("title", f"Story {len(scenes)+1}"),
            "quote": obj.get("quote", ""),
            "image_prompt": obj.get("image_prompt", ""),
        })
    titles = ", ".join(s["title"] for s in scenes)
    return {
        "summary": f"{len(scenes)} invented stories, one image each: {titles}.",
        "style": "painterly cinematic stills, one per story",
        "scenes": scenes,
    }


def choose_scenes(session: dict, session_id: str, n: int, llm_spec: str) -> dict:
    meta = sess.session_metadata(session)
    digest = _build_digest(session)
    user = (
        f"SESSION: {session_id}\n"
        f"TECHNIQUE: {meta.get('technique_name') or meta.get('technique')}\n"
        f"TARGET MODEL: {meta.get('target')}\n\n"
        f"{digest}"
    )
    system = SYSTEM_PROMPT.replace("__N__", str(n))
    obj = llm.chat_json(llm_spec, system, user, max_tokens=4096)
    scenes = obj.get("scenes", [])[:n]
    return {"summary": obj.get("summary", ""), "style": obj.get("style", ""), "scenes": scenes}


def render_scene(image_prompt: str, dest: Path) -> None:
    result = fal_helpers.run_with_retry(
        config.FAL_KEYFRAME_MODEL,
        {
            "prompt": image_prompt.strip() + STYLE_SUFFIX,
            "num_images": 1,
            "aspect_ratio": config.FAL_KEYFRAME_ASPECT_RATIO,
            "resolution": config.FAL_KEYFRAME_RESOLUTION,
        },
    )
    url = result["images"][0]["url"]
    fal_helpers.download(url, dest)


def make_scenes(arg: str, n: int = 5, llm_spec: str = DEFAULT_SCENE_LLM,
                regen: bool = False, per_story: bool | None = None,
                min_chars: int = 400) -> Path:
    src = _resolve(arg)
    session_id = src.stem
    session = sess.load_session(src)
    meta = sess.session_metadata(session)
    out_dir = SCENES_ROOT / session_id
    out_dir.mkdir(parents=True, exist_ok=True)
    scenes_json = out_dir / "scenes.json"

    # Narrative elicitation = a suite of distinct stories; render one image per
    # story rather than summarising the whole session into N scenes.
    if per_story is None:
        per_story = meta.get("technique") == "narrative_elicitation"

    # Re-use an existing plan unless asked to regenerate (image render is the
    # expensive, resumable part).
    if scenes_json.exists() and not regen:
        plan = json.loads(scenes_json.read_text())
        print(f"[scenes] reusing plan for {session_id} ({len(plan['scenes'])} scenes)")
    else:
        print(f"[scenes] directing {session_id} via {llm_spec} "
              f"({'per-story' if per_story else 'summary'}) …")
        chosen = (
            choose_scenes_per_story(session, llm_spec, min_chars)
            if per_story
            else choose_scenes(session, session_id, n, llm_spec)
        )
        plan = {
            "session": session_id,
            "target": meta.get("target"),
            "technique": meta.get("technique"),
            "technique_name": meta.get("technique_name"),
            "summary": chosen["summary"],
            "style": chosen["style"],
            "scenes": [
                {
                    "index": i,
                    "title": s.get("title", f"Scene {i}"),
                    "quote": s.get("quote", ""),
                    "image_prompt": s.get("image_prompt", ""),
                    "file": f"scene_{i:02d}.png",
                }
                for i, s in enumerate(chosen["scenes"], start=1)
            ],
        }
        scenes_json.write_text(json.dumps(plan, indent=2))
        print(f"[scenes]   chose {len(plan['scenes'])} scenes")

    for s in plan["scenes"]:
        dest = out_dir / s["file"]
        if dest.exists() and not regen:
            print(f"[scenes]   ✓ {s['file']} (exists)")
            continue
        print(f"[scenes]   → rendering {s['file']}: {s['title']}")
        try:
            render_scene(s["image_prompt"], dest)
            print(f"[scenes]   ✓ {s['file']}")
        except Exception as e:  # noqa: BLE001
            print(f"[scenes]   ✗ {s['file']} failed: {e}")

    print(f"[scenes] done → {out_dir}")
    return out_dir


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("session", help="Session id or path to session.json")
    ap.add_argument("-n", "--num", type=int, default=5, help="Max scenes (default 5)")
    ap.add_argument("--llm", default=DEFAULT_SCENE_LLM, help="provider:model spec")
    ap.add_argument("--regen", action="store_true", help="Re-plan and re-render everything")
    ap.add_argument("--per-story", dest="per_story", action="store_true", default=None,
                    help="One image per story-turn (auto for narrative_elicitation)")
    ap.add_argument("--min-chars", type=int, default=400,
                    help="Min target-turn length to count as a story (per-story mode)")
    args = ap.parse_args()
    make_scenes(args.session, n=args.num, llm_spec=args.llm, regen=args.regen,
                per_story=args.per_story, min_chars=args.min_chars)


if __name__ == "__main__":
    main()
