"""
Kerberos Protocol — Session Scorer

Reads a session .json produced by runner.py, identifies its phase from
metadata.technique, dispatches the appropriate scorers from the instrument
registry, writes a <session>_scores.json next to it.

Usage:
    # Score one session
    python score_session.py sessions/llama_wat_20260524.json --rater anthropic:claude-opus-4-7

    # Score all sessions in a directory
    python score_session.py sessions/ --rater anthropic:claude-opus-4-7

    # Restrict to specific instruments
    python score_session.py sessions/foo.json --instruments dmrs,wrad,epistemic_markers

    # Layer 1 only (automated + DMRS) — fastest, cheapest
    python score_session.py sessions/foo.json --layer 1

Output: sessions/<session_name>_scores.json with shape:
    {
      "session": "<path>",
      "technique": "...",
      "phase": "wat|shadow|narrative|ai|stems",
      "results": {
        "dmrs": {scores, evidence, metadata},
        "wrad": {...},
        ...
      }
    }
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

# Ensure repo root is importable
sys.path.insert(0, str(Path(__file__).resolve().parent))

from scorers.base import (
    INSTRUMENT_REGISTRY,
    _ensure_scorers_imported,
    get_scorers_for_phase,
)
from scorers.llm_rater._rater import DEFAULT_RATER


TECHNIQUE_TO_PHASE = {
    "wat": "wat",
    "word_association_test": "wat",
    "shadow_probing": "shadow",
    "shadow": "shadow",
    "narrative_elicitation": "narrative",
    "narrative": "narrative",
    "active_imagination": "ai",
    "ai": "ai",
    "loevinger_stems": "stems",
    "stems": "stems",
}

LAYER_1_INSTRUMENTS = {"dmrs", "gottschalk_gleser", "wrad"}


def load_session(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


def collect_target_text(session: dict, joiner: str = "\n\n") -> str:
    """Concatenate all target responses with turn labels."""
    parts = []
    for t in session.get("turns", []):
        if t.get("role") == "target":
            text = (t.get("conversation") or t.get("raw") or "").strip()
            parts.append(f"[Turn {t.get('turn', '?')}] {text}")
    return joiner.join(parts)


def collect_stems_text(session: dict) -> str:
    """For loevinger_stems sessions: extract stem|||completion pairs.

    Pairs each interrogator stimulus (the stem) with the target's next
    response (the completion). Returns a newline-separated block.
    """
    turns = session.get("turns", [])
    pairs = []
    for i, t in enumerate(turns):
        if t.get("role") != "interrogator":
            continue
        stem = (t.get("conversation") or "").strip()
        if not stem.endswith("..."):
            # not a stem prompt — skip framing turns
            if not stem or len(stem) > 200:
                continue
        completion = None
        for t2 in turns[i + 1:]:
            if t2.get("role") == "target":
                completion = (t2.get("conversation") or "").strip()
                break
            if t2.get("role") == "interrogator":
                break
        if completion is not None:
            pairs.append(f"{stem} ||| {completion}")
    return "\n".join(pairs)


def collect_cot_traces(session: dict) -> str:
    """Extract CoT/thinking traces from target turns if present.
    Targets that expose thinking are marked via turn['thinking'] or
    embedded <thinking>...</thinking> tags in raw output.
    """
    import re
    parts = []
    for t in session.get("turns", []):
        if t.get("role") != "target":
            continue
        if t.get("thinking"):
            parts.append(f"[Turn {t.get('turn')}] {t['thinking']}")
            continue
        raw = t.get("raw", "") or ""
        m = re.search(r"<thinking>(.*?)</thinking>", raw, re.DOTALL)
        if m:
            parts.append(f"[Turn {t.get('turn')}] {m.group(1).strip()}")
    return "\n\n".join(parts)


def filter_scorers(phase: str, instruments: list[str] | None, layer: int | None) -> list:
    _ensure_scorers_imported()
    scorers = get_scorers_for_phase(phase)
    if instruments:
        wanted = {i.strip() for i in instruments}
        scorers = [s for s in scorers if s.instrument_id in wanted]
    if layer == 1:
        scorers = [s for s in scorers if s.instrument_id in LAYER_1_INSTRUMENTS]
    return scorers


def score_session(
    session_path: Path,
    rater: str = DEFAULT_RATER,
    instruments: list[str] | None = None,
    layer: int | None = None,
) -> dict:
    session = load_session(session_path)
    metadata = session.get("metadata", {})
    technique = metadata.get("technique", "")
    phase = TECHNIQUE_TO_PHASE.get(technique, "any")

    scorers = filter_scorers(phase, instruments, layer)
    target_text = collect_target_text(session)
    stems_text = collect_stems_text(session) if phase == "stems" else ""
    cot_text = collect_cot_traces(session)

    print(f"[score_session] {session_path.name}")
    print(f"  technique: {technique}  phase: {phase}")
    print(f"  target text: {len(target_text)} chars  CoT: {len(cot_text)} chars")
    print(f"  scorers ({len(scorers)}): {[s.instrument_id for s in scorers]}")

    results: dict = {}
    for scorer in scorers:
        sid = scorer.instrument_id
        t0 = time.monotonic()
        try:
            if sid == "jung_wat":
                result = scorer.score_session(session, rater=rater)
            elif sid == "loevinger":
                if not stems_text:
                    print(f"  [skip] {sid}: no stem/completion pairs in session")
                    continue
                result = scorer.score(stems_text, context={"rater": rater})
            elif sid == "tli":
                if not cot_text:
                    print(f"  [skip] tli: no CoT traces in session")
                    continue
                result = scorer.score(cot_text, context={"rater": rater})
            else:
                # default: score concatenated target text
                if not target_text:
                    print(f"  [skip] {sid}: no target text")
                    continue
                result = scorer.score(target_text, context={"rater": rater})
            results[sid] = result
            elapsed = int((time.monotonic() - t0) * 1000)
            print(f"  [ok] {sid} ({elapsed} ms)")
        except Exception as e:
            print(f"  [err] {sid}: {type(e).__name__}: {e}")
            results[sid] = {
                "instrument": sid,
                "scores": {},
                "evidence": [],
                "metadata": {"error": f"{type(e).__name__}: {e}"},
            }

    return {
        "session": str(session_path),
        "technique": technique,
        "phase": phase,
        "rater": rater,
        "results": results,
    }


def _invoke_scorer_sync(scorer, session, target_text, stems_text, cot_text, rater):
    """Shared per-scorer dispatch. Returns (instrument_id, result_dict)."""
    sid = scorer.instrument_id
    try:
        if sid == "jung_wat":
            result = scorer.score_session(session, rater=rater)
        elif sid == "loevinger":
            if not stems_text:
                return sid, {"_skipped": "no stem/completion pairs"}
            result = scorer.score(stems_text, context={"rater": rater})
        elif sid == "tli":
            if not cot_text:
                return sid, {"_skipped": "no CoT traces"}
            result = scorer.score(cot_text, context={"rater": rater})
        else:
            if not target_text:
                return sid, {"_skipped": "no target text"}
            result = scorer.score(target_text, context={"rater": rater})
        return sid, result
    except Exception as e:
        return sid, {
            "instrument": sid,
            "scores": {},
            "evidence": [],
            "metadata": {"error": f"{type(e).__name__}: {e}"},
        }


async def score_session_async(
    session_path: Path,
    rater: str = DEFAULT_RATER,
    instruments: list[str] | None = None,
    layer: int | None = None,
    concurrency: int = 8,
) -> dict:
    """Concurrent variant of score_session.

    Each scorer's sync .score() runs in its own thread via asyncio.to_thread,
    capped by a semaphore. The rater backend uses the existing sync
    chat()/run() path under the hood — parallelism comes from running multiple
    scorers at once, each making an independent rater call.
    """
    session = load_session(session_path)
    metadata = session.get("metadata", {})
    technique = metadata.get("technique", "")
    phase = TECHNIQUE_TO_PHASE.get(technique, "any")

    scorers = filter_scorers(phase, instruments, layer)
    target_text = collect_target_text(session)
    stems_text = collect_stems_text(session) if phase == "stems" else ""
    cot_text = collect_cot_traces(session)

    print(f"[score_session_async] {session_path.name}")
    print(f"  technique: {technique}  phase: {phase}")
    print(f"  scorers ({len(scorers)}): {[s.instrument_id for s in scorers]}  concurrency={concurrency}")

    semaphore = asyncio.Semaphore(max(1, concurrency))

    async def run_one(scorer):
        async with semaphore:
            t0 = time.monotonic()
            sid, result = await asyncio.to_thread(
                _invoke_scorer_sync, scorer, session, target_text, stems_text, cot_text, rater
            )
            elapsed = int((time.monotonic() - t0) * 1000)
            if isinstance(result, dict) and result.get("_skipped"):
                print(f"  [skip] {sid}: {result['_skipped']}")
                return sid, None
            err = (result.get("metadata") or {}).get("error") if isinstance(result, dict) else None
            print(f"  [{'err' if err else 'ok'}] {sid} ({elapsed} ms){' ' + err if err else ''}")
            return sid, result

    pairs = await asyncio.gather(*[run_one(s) for s in scorers])
    results = {sid: r for sid, r in pairs if r is not None}

    return {
        "session": str(session_path),
        "technique": technique,
        "phase": phase,
        "rater": rater,
        "results": results,
    }


def score_all(directory: Path, **kwargs) -> list[dict]:
    sessions = sorted([
        p for p in directory.glob("*.json")
        if not p.name.endswith("_scores.json") and not p.name.endswith("_findings.json")
    ])
    out = []
    for p in sessions:
        result = score_session(p, **kwargs)
        out_path = p.with_name(p.stem + "_scores.json")
        out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False))
        print(f"  -> {out_path}")
        out.append(result)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Kerberos — apply scorers to a session JSON")
    parser.add_argument("input", help="Session .json file or directory of sessions")
    parser.add_argument("--rater", default=DEFAULT_RATER, help=f"Rater model spec (default: {DEFAULT_RATER})")
    parser.add_argument("--instruments", help="Comma-separated instrument ids to restrict to")
    parser.add_argument("--layer", type=int, choices=[1], help="If 1, run only Layer 1 (always-on) scorers")
    parser.add_argument("--output", "-o", help="Output path (default: <session>_scores.json)")
    parser.add_argument("--concurrency", "-c", type=int, default=1,
                        help="Number of scorers to run in parallel (default: 1 = sequential). "
                             "Use 8+ when the rater is OpenRouter or another high-throughput provider.")
    args = parser.parse_args()

    instruments = args.instruments.split(",") if args.instruments else None
    in_path = Path(args.input)
    use_async = args.concurrency > 1

    def _score_one(p: Path) -> dict:
        if use_async:
            return asyncio.run(score_session_async(
                p, rater=args.rater, instruments=instruments,
                layer=args.layer, concurrency=args.concurrency,
            ))
        return score_session(p, rater=args.rater, instruments=instruments, layer=args.layer)

    if in_path.is_dir():
        sessions = sorted([
            p for p in in_path.glob("*.json")
            if not p.name.endswith("_scores.json") and not p.name.endswith("_findings.json")
        ])
        for p in sessions:
            result = _score_one(p)
            out_path = p.with_name(p.stem + "_scores.json")
            out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False))
            print(f"  -> {out_path}")
        return

    result = _score_one(in_path)
    out_path = Path(args.output) if args.output else in_path.with_name(in_path.stem + "_scores.json")
    out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    main()
