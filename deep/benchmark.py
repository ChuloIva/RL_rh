"""
Kerberos Benchmark — Cross-Model Orchestrator

Runs the full Kerberos battery against one or more target models, scores every
session with the appropriate instruments, aggregates into per-model profiles,
and writes a cross-model score matrix as JSON + HTML.

Usage:
    # Full battery on two targets, default rater
    python benchmark.py \
        --targets openrouter:meta-llama/llama-3.1-70b-instruct,anthropic:claude-sonnet-4-6 \
        --rater anthropic:claude-opus-4-7

    # Phase 1 only (faster smoke test)
    python benchmark.py \
        --targets openrouter:google/gemini-2.5-flash \
        --rater anthropic:claude-opus-4-7 \
        --phases 1 \
        --turns 30

    # Skip scoring (just collect sessions)
    python benchmark.py --targets ... --no-score

Phase → technique mapping:
    1 = wat
    2 = shadow_probing
    3 = narrative_elicitation, active_imagination, loevinger_stems

Output:
    sessions/<safe_target>_<technique>_<ts>.json    (raw sessions)
    sessions/<safe_target>_<technique>_<ts>_scores.json  (per-session scores)
    reports/<safe_target>_profile.json              (aggregated per-model profile)
    reports/benchmark.json                          (cross-model matrix)
    deep/benchmark.html                             (interactive viewer reads benchmark.json)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from runner import run_session
from score_session import score_session, score_session_async, TECHNIQUE_TO_PHASE
from scorers.base import _ensure_scorers_imported
from scorers.llm_rater._rater import DEFAULT_RATER


REPO_ROOT = Path(__file__).resolve().parent
TECHNIQUES_DIR = REPO_ROOT / "techniques"
SESSIONS_DIR = REPO_ROOT / "sessions"
REPORTS_DIR = REPO_ROOT / "reports"


PHASE_TECHNIQUES = {
    1: ["word_association_test"],
    2: ["shadow_probing"],
    3: ["narrative_elicitation", "active_imagination", "loevinger_stems"],
}


def _safe_model_id(spec: str) -> str:
    """Match runner.py's filename convention: drop provider prefix, then sanitize."""
    model = spec.split(":", 1)[1] if ":" in spec else spec
    return model.replace("/", "_").replace(":", "_")


def _technique_path(name: str) -> Path:
    return TECHNIQUES_DIR / f"{name}.json"


def _latest_session_for(target: str, technique_id: str) -> Path | None:
    """Find the most-recent session file for (target, technique)."""
    safe = _safe_model_id(target)
    # technique_id may be "wat" while file is named "word_association_test" — both possible
    candidates = sorted(SESSIONS_DIR.glob(f"{safe}_*.json"), reverse=True)
    for p in candidates:
        if p.name.endswith("_scores.json") or p.name.endswith("_findings.json"):
            continue
        try:
            data = json.loads(p.read_text())
        except Exception:
            continue
        if data.get("metadata", {}).get("technique") == technique_id:
            return p
    return None


def _aggregate_profile(target: str, score_files: list[Path]) -> dict:
    """Combine all per-session score JSONs into a single profile."""
    profile: dict = {
        "target": target,
        "sessions_scored": len(score_files),
        "instruments": {},
    }
    for sf in score_files:
        try:
            data = json.loads(sf.read_text())
        except Exception as e:
            print(f"  [warn] could not load {sf}: {e}")
            continue
        phase = data.get("phase")
        results = data.get("results", {})
        for instrument, result in results.items():
            scores = result.get("scores", {})
            entry = profile["instruments"].setdefault(instrument, {
                "phase_runs": [],
                "scores_by_phase": {},
                "evidence_count": 0,
            })
            entry["phase_runs"].append({
                "phase": phase,
                "session": Path(data.get("session", "")).name,
                "scores": scores,
                "evidence_count": len(result.get("evidence", [])),
            })
            entry["scores_by_phase"][phase] = scores
            entry["evidence_count"] += len(result.get("evidence", []))
    return profile


def run_target(
    target: str,
    interrogator: str,
    rater: str,
    phases: list[int],
    turns: int,
    score: bool,
    auto_extract: bool,
    score_concurrency: int = 1,
) -> dict:
    """Run all selected phases against one target, score, aggregate.

    Internal phase loop is sequential per target (findings chain between phases).
    Scoring within each phase can run concurrently when score_concurrency > 1.
    """
    print(f"\n{'=' * 60}\nTARGET: {target}\n{'=' * 60}")

    findings_path: str | None = None
    sessions_run: list[Path] = []

    for phase_num in phases:
        for tech_name in PHASE_TECHNIQUES.get(phase_num, []):
            tech_path = _technique_path(tech_name)
            if not tech_path.exists():
                print(f"[skip] no technique file: {tech_path}")
                continue
            tech_data = json.loads(tech_path.read_text())
            tech_id = tech_data["technique"]["id"]
            print(f"\n--- Phase {phase_num} : {tech_id} [{target}] ---")
            try:
                run_session(
                    technique_path=str(tech_path),
                    interrogator_spec=interrogator,
                    target_spec=target,
                    max_turns=turns,
                    findings_path=findings_path,
                    auto_extract=auto_extract,
                )
            except Exception as e:
                print(f"[err] session for {tech_id} failed: {e}")
                continue
            session_path = _latest_session_for(target, tech_id)
            if session_path:
                sessions_run.append(session_path)
                fp_candidate = session_path.with_name(session_path.stem + "_findings.json")
                if fp_candidate.exists():
                    findings_path = str(fp_candidate)
            else:
                print(f"[warn] could not locate session output for {tech_id}")

    score_files: list[Path] = []
    if score:
        _ensure_scorers_imported()
        for session_path in sessions_run:
            print(f"\n[score] {session_path.name}")
            try:
                if score_concurrency > 1:
                    result = asyncio.run(score_session_async(
                        session_path, rater=rater, concurrency=score_concurrency,
                    ))
                else:
                    result = score_session(session_path, rater=rater)
                scores_path = session_path.with_name(session_path.stem + "_scores.json")
                scores_path.write_text(json.dumps(result, indent=2, ensure_ascii=False))
                score_files.append(scores_path)
                print(f"  -> {scores_path.name}")
            except Exception as e:
                print(f"  [err] scoring failed: {e}")

    profile = _aggregate_profile(target, score_files)
    REPORTS_DIR.mkdir(exist_ok=True)
    profile_path = REPORTS_DIR / f"{_safe_model_id(target)}_profile.json"
    profile_path.write_text(json.dumps(profile, indent=2, ensure_ascii=False))
    print(f"\n[profile] {profile_path}")
    return profile


async def _run_target_async(target: str, semaphore: asyncio.Semaphore, **kwargs) -> dict:
    """Async wrapper: run_target is sync (long sequential I/O loop), so we
    push it to a thread. The semaphore caps how many targets run concurrently."""
    async with semaphore:
        return await asyncio.to_thread(run_target, target=target, **kwargs)


async def run_all_targets_async(targets: list[str], parallel_targets: int, **kwargs) -> list[dict]:
    semaphore = asyncio.Semaphore(max(1, parallel_targets))
    return await asyncio.gather(*[
        _run_target_async(t, semaphore, **kwargs) for t in targets
    ])


def build_matrix(profiles: list[dict]) -> dict:
    """Build the cross-model matrix consumed by benchmark.html."""
    matrix: dict = {
        "generated": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "targets": [],
        "instruments": [],
        "cells": {},  # cells[target][instrument] = {headline_score, all_scores, evidence_count}
    }
    instrument_set: set[str] = set()
    for p in profiles:
        target = p["target"]
        matrix["targets"].append(target)
        matrix["cells"][target] = {}
        for instr, entry in p.get("instruments", {}).items():
            instrument_set.add(instr)
            headline = _extract_headline(instr, entry)
            matrix["cells"][target][instr] = {
                "headline": headline,
                "all_scores": entry.get("scores_by_phase", {}),
                "evidence_count": entry.get("evidence_count", 0),
                "n_phases": len(entry.get("phase_runs", [])),
            }
    matrix["instruments"] = sorted(instrument_set)
    return matrix


_HEADLINE_KEY = {
    "dmrs": "odf",
    "wrad": "wrad_mean",
    "epistemic_markers": "hedge_to_booster_ratio",
    "gottschalk_gleser": "anxiety_total_normalized",
    "rfs": "rfs",
    "experiencing": "level",
    "integrative_complexity": "ic",
    "scors_g": "mean",
    "holt": "rego",
    "loevinger": "weighted_mean_stage",
    "tli": "total",
    "jung_wat": "n_pairs",
}


def _extract_headline(instrument: str, entry: dict) -> float | int | str | None:
    """Pick a single headline number per instrument across phases (mean across phases when numeric)."""
    key = _HEADLINE_KEY.get(instrument)
    if not key:
        return None
    values: list[float] = []
    for phase, scores in entry.get("scores_by_phase", {}).items():
        v = scores.get(key)
        if isinstance(v, (int, float)):
            values.append(float(v))
    if not values:
        return None
    return round(sum(values) / len(values), 4)


def main() -> None:
    parser = argparse.ArgumentParser(description="Kerberos Benchmark — cross-model end-to-end orchestrator")
    parser.add_argument("--targets", required=True,
                        help="Comma-separated list of target model specs (provider:model)")
    parser.add_argument("--interrogator", "-i", default="anthropic:claude-sonnet-4-6",
                        help="Interrogator model spec (default: anthropic:claude-sonnet-4-6)")
    parser.add_argument("--rater", default=DEFAULT_RATER,
                        help=f"Scoring rater model spec (default: {DEFAULT_RATER})")
    parser.add_argument("--phases", default="1,2,3",
                        help="Comma-separated phase numbers to run (default: 1,2,3)")
    parser.add_argument("--turns", "-n", type=int, default=40,
                        help="Max turns per session (default: 40)")
    parser.add_argument("--no-score", action="store_true",
                        help="Run sessions only, skip scoring")
    parser.add_argument("--no-extract", action="store_true",
                        help="Skip automatic findings extraction between sessions")
    parser.add_argument("--out", default=str(REPORTS_DIR),
                        help="Output directory for profiles + matrix (default: reports/)")
    parser.add_argument("--parallel-targets", type=int, default=1,
                        help="How many target models to benchmark in parallel (default: 1). "
                             "Each target's phase loop is sequential (findings chain), but multiple "
                             "targets can run concurrently. Use 2-4 with OpenRouter, fewer with Anthropic.")
    parser.add_argument("--score-concurrency", type=int, default=1,
                        help="How many scorers to run in parallel within each session (default: 1). "
                             "Use 8+ with OpenRouter as rater. Multiplies with --parallel-targets.")
    args = parser.parse_args()

    targets = [t.strip() for t in args.targets.split(",") if t.strip()]
    phases = [int(p) for p in args.phases.split(",") if p.strip()]
    common_kwargs = dict(
        interrogator=args.interrogator,
        rater=args.rater,
        phases=phases,
        turns=args.turns,
        score=not args.no_score,
        auto_extract=not args.no_extract,
        score_concurrency=args.score_concurrency,
    )

    if args.parallel_targets > 1 and len(targets) > 1:
        print(f"Running {len(targets)} targets with up to {args.parallel_targets} in parallel.")
        profiles = asyncio.run(run_all_targets_async(
            targets, args.parallel_targets, **common_kwargs,
        ))
    else:
        profiles = [run_target(target=t, **common_kwargs) for t in targets]

    matrix = build_matrix(profiles)
    out_dir = Path(args.out)
    out_dir.mkdir(exist_ok=True)
    matrix_path = out_dir / "benchmark.json"
    matrix_path.write_text(json.dumps(matrix, indent=2, ensure_ascii=False))

    print(f"\n{'=' * 60}")
    print(f"BENCHMARK COMPLETE")
    print(f"Targets: {len(targets)}")
    print(f"Matrix: {matrix_path}")
    print(f"Open: deep/benchmark.html")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
