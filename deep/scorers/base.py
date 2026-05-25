"""
Scorer base — protocol, result shape, and registry.

Every scorer module registers itself at import time via @register(...) so that
score_session.py can dispatch by phase without hard-coding the instrument list.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Protocol, TypedDict, runtime_checkable


INSTRUMENTS_DIR = Path(__file__).resolve().parent.parent / "instruments"


PHASE_TAGS = {
    "any",          # always-on (Layer 1: dmrs, gottschalk, wrad)
    "wat",          # word association test
    "shadow",       # shadow probing
    "narrative",    # TAT-style elicitation
    "ai",           # active imagination
    "stems",        # loevinger sentence stems
    "cot",          # CoT trace analysis (thinking-mode targets)
}


class Evidence(TypedDict, total=False):
    text: str         # the supporting span from the source
    rationale: str    # rater's reason
    location: str     # e.g. "turn 7 target response"
    tags: list[str]   # instrument-specific tags (defense name, level, scale)


class ScoreMetadata(TypedDict, total=False):
    rater_model: str
    rater_provider: str
    input_tokens: int
    output_tokens: int
    elapsed_ms: int
    schema_version: str
    n_retries: int


class ScoreResult(TypedDict):
    instrument: str       # e.g. "dmrs"
    scores: dict          # instrument-specific score dict
    evidence: list        # list[Evidence] — supporting spans + rationale
    metadata: dict        # ScoreMetadata


@runtime_checkable
class Scorer(Protocol):
    instrument_id: str
    applies_to: list[str]  # phase tags from PHASE_TAGS

    def score(self, text: str, context: dict | None = None) -> ScoreResult: ...


INSTRUMENT_REGISTRY: dict[str, Scorer] = {}


def register(scorer: Scorer) -> Scorer:
    """Decorator-style registration. Called at module import time."""
    instrument_id = getattr(scorer, "instrument_id", None)
    if not instrument_id:
        raise ValueError(f"Scorer {scorer!r} missing instrument_id")
    for tag in getattr(scorer, "applies_to", []):
        if tag not in PHASE_TAGS:
            raise ValueError(f"Scorer {instrument_id}: unknown phase tag {tag!r}")
    INSTRUMENT_REGISTRY[instrument_id] = scorer
    return scorer


def get_scorers_for_phase(phase: str) -> list[Scorer]:
    """Return all scorers whose applies_to includes the given phase or 'any'."""
    if phase not in PHASE_TAGS:
        raise ValueError(f"Unknown phase {phase!r}. Valid: {sorted(PHASE_TAGS)}")
    out = []
    for scorer in INSTRUMENT_REGISTRY.values():
        if phase in scorer.applies_to or "any" in scorer.applies_to:
            out.append(scorer)
    return out


_INSTRUMENT_FILES = {
    "dmrs": "dmrs.json",
    "gottschalk_gleser": "gottschalk_gleser.json",
    "wrad": "wrad.json",
    "epistemic_markers": "epistemic_markers.json",
    "rfs": "rfs_scale.json",
    "experiencing": "experiencing_scale.json",
    "integrative_complexity": "integrative_complexity_scale.json",
    "scors_g": "scors_g.json",
    "holt": "holt_primary_process.json",
    "loevinger": "loevinger_wusct.json",
    "tli": "tli.json",
    "jung_wat": "jung_wat.json",
}


def load_instrument(instrument_id: str) -> dict:
    """Load the canonical instrument JSON by id."""
    fname = _INSTRUMENT_FILES.get(instrument_id)
    if fname:
        path = INSTRUMENTS_DIR / fname
        if path.exists():
            with open(path) as f:
                return json.load(f)
    # fall back to convention-based search
    for candidate in (
        INSTRUMENTS_DIR / f"{instrument_id}.json",
        INSTRUMENTS_DIR / f"{instrument_id}_scale.json",
    ):
        if candidate.exists():
            with open(candidate) as f:
                return json.load(f)
    raise FileNotFoundError(f"No instrument JSON found for {instrument_id!r}")


def make_result(
    instrument: str,
    scores: dict,
    evidence: list | None = None,
    metadata: dict | None = None,
) -> ScoreResult:
    """Helper to build a well-formed ScoreResult."""
    return {
        "instrument": instrument,
        "scores": scores,
        "evidence": evidence or [],
        "metadata": metadata or {},
    }


def _ensure_scorers_imported() -> None:
    """Import all scorer modules so they register themselves.

    score_session.py calls this once at startup before iterating the registry.
    """
    # Automated
    from scorers.automated import wrad, epistemic  # noqa: F401
    # Hybrid
    from scorers.hybrid import wat_indicators  # noqa: F401
    # LLM-raters
    from scorers.llm_rater import (  # noqa: F401
        dmrs,
        gottschalk,
        rfs,
        experiencing,
        integrative,
        scors_g,
        holt,
        loevinger,
        tli,
    )


def all_scorers() -> dict[str, Scorer]:
    """Convenience: ensure imports happened, then return the registry."""
    _ensure_scorers_imported()
    return INSTRUMENT_REGISTRY
