"""Stage 1 — Scene extraction.

For each target turn in a Kerberos session, ask an LLM (via OpenRouter by
default) to break the response into shots: image_prompt, motion_hint,
ambient_audio_hint, subtitle, duration, continuity.

Idempotent: skips turns already present in the manifest.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from video import config, llm, manifest as mf, session as sess


def _load_prompt() -> str:
    return (config.PROMPTS_DIR / "scene_extractor.md").read_text()


def _build_user_message(
    turn: sess.TargetTurn,
    registry: list[dict],
    style_notes: str,
) -> str:
    return (
        f"## Turn {turn.turn}\n\n"
        f"### Analyst prompt\n{turn.prior_prompt}\n\n"
        f"### Target response\n{turn.target_text}\n\n"
        f"### Entity registry so far\n"
        f"{json.dumps(registry, indent=2) if registry else '(empty)'}\n\n"
        f"### Style notes\n{style_notes or '(none yet)'}\n"
    )


def _clamp_shots(shots: list[dict]) -> list[dict]:
    return shots[: config.MAX_SHOTS_PER_TURN]


def _enforce_durations(shots: list[dict]) -> list[dict]:
    for s in shots:
        d = int(s.get("duration_sec", config.DEFAULT_SHOT_DURATION))
        s["duration_sec"] = max(config.MIN_SHOT_DURATION,
                                min(config.MAX_SHOT_DURATION, d))
    return shots


def _assign_ids(turn: int, shots: list[dict]) -> list[dict]:
    for i, s in enumerate(shots, start=1):
        s["id"] = f"t{turn:02d}_s{i}"
    return shots


def extract(source_path: str, llm_spec: str | None = None,
            style_notes: str = "") -> dict:
    session_id = mf.session_id_from(source_path)
    manifest = mf.load_or_init(session_id, source_path)

    if manifest["stages"]["extract"]["status"] == "done":
        print(f"[extract] already done for {session_id}")
        return manifest

    session = sess.load_session(source_path)
    turns = sess.target_turns(session)
    print(f"[extract] {session_id}: {len(turns)} target turns")

    extract_dir = config.session_out_dir(session_id) / "turns"
    extract_dir.mkdir(parents=True, exist_ok=True)

    system_prompt = _load_prompt()
    registry: list[dict] = []
    spec = llm_spec or config.DEFAULT_LLM
    turns_done: list[int] = manifest["stages"]["extract"].get("turns_done", [])
    shot_budget = config.MAX_SHOTS_PER_SESSION

    for turn in turns:
        # Always reload registry from disk to support resume
        out_path = config.turn_dir(session_id, turn.turn) / "extraction.json"
        if out_path.exists():
            existing = json.loads(out_path.read_text())
            for d in existing.get("registry_delta", []):
                if not any(r["id"] == d["id"] for r in registry):
                    registry.append(d)
            shot_budget -= len(existing.get("shots", []))
            if turn.turn not in turns_done:
                turns_done.append(turn.turn)
            continue

        if shot_budget <= 0:
            print(f"[extract] shot budget exhausted at turn {turn.turn}")
            break

        user = _build_user_message(turn, registry, style_notes)
        print(f"[extract] turn {turn.turn} → LLM ({spec})")
        try:
            obj = llm.chat_json(spec, system_prompt, user)
        except Exception as e:  # noqa: BLE001
            print(f"[extract] turn {turn.turn} failed: {e}")
            raise

        shots = _enforce_durations(_clamp_shots(obj.get("shots", [])))
        if shot_budget < len(shots):
            shots = shots[:shot_budget]
        shots = _assign_ids(turn.turn, shots)
        shot_budget -= len(shots)

        delta = obj.get("registry_delta", []) or []
        for d in delta:
            if not any(r["id"] == d["id"] for r in registry):
                d.setdefault("first_seen_turn", turn.turn)
                registry.append(d)

        out = {
            "turn": turn.turn,
            "shots": shots,
            "registry_delta": delta,
            "target_text": turn.target_text,
            "analyst_prompt": turn.prior_prompt,
        }
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(out, indent=2))
        turns_done.append(turn.turn)

        for s in shots:
            manifest["shots"][s["id"]] = {
                "turn": turn.turn,
                "duration_sec": s["duration_sec"],
                "keyframe": None,
                "video": None,
            }

        manifest["stages"]["extract"]["turns_done"] = turns_done
        mf.save(session_id, manifest)
        print(f"[extract]   {len(shots)} shots, budget left {shot_budget}")

    manifest["stages"]["extract"]["status"] = "done"
    manifest["stages"]["extract"]["turns_done"] = turns_done
    manifest["registry"] = registry
    mf.save(session_id, manifest)
    print(f"[extract] done. total shots: {len(manifest['shots'])}")
    return manifest


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("source", help="Path to Kerberos session .json")
    p.add_argument("--llm", default=None, help="provider:model spec")
    p.add_argument("--style", default="", help="optional style notes")
    args = p.parse_args()
    extract(args.source, llm_spec=args.llm, style_notes=args.style)


if __name__ == "__main__":
    main()
