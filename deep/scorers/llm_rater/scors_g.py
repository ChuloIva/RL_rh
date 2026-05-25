"""SCORS-G scorer — Westen / Stein object relations dimensions."""

from __future__ import annotations
from typing import ClassVar

from scorers.base import ScoreResult, load_instrument, make_result, register
from scorers.llm_rater._rater import DEFAULT_RATER, run as rater_run


DIMENSIONS = ["COM", "AFF", "EIR", "EIM", "SC", "AGG", "SE", "ICS"]

DEFAULTS = {"AFF": 4, "EIM": 4, "AGG": 4, "SE": 4}


def _per_dim_schema() -> dict:
    return {
        dim: {
            "score": "integer 1-7 (or use default per manual when content absent)",
            "rationale": "string ≤ 2 sentences",
            "evidence": [{"text": "verbatim span", "rationale": "string"}]
        }
        for dim in DIMENSIONS
    }


_OUTPUT_SCHEMA = {
    "dimensions": _per_dim_schema(),
    "narrative_summary": "string — overall object-relations summary"
}


class SCORSGScorer:
    instrument_id: ClassVar[str] = "scors_g"
    applies_to: ClassVar[list[str]] = ["narrative", "ai"]
    _instrument: dict = load_instrument("scors_g")

    def score(self, text: str, context: dict | None = None) -> ScoreResult:
        rater = (context or {}).get("rater", DEFAULT_RATER)
        parsed, meta = rater_run(
            instrument=self._instrument,
            text=text,
            output_schema=_OUTPUT_SCHEMA,
            rater=rater,
            instructions=(
                "Score each of the 8 dimensions on the 1-7 scale. Use the default score of 4 for "
                "AFF, EIM, AGG, and SE when relevant content is absent from the narrative. "
                "Provide at least one evidence span per dimension where possible."
            ),
        )
        dims = parsed.get("dimensions", {})
        scores: dict = {}
        evidence: list = []
        for dim in DIMENSIONS:
            entry = dims.get(dim) or {}
            score = entry.get("score")
            if score is None and dim in DEFAULTS:
                score = DEFAULTS[dim]
            scores[dim] = score
            for ev in entry.get("evidence", []):
                evidence.append({
                    "text": ev.get("text", ""),
                    "rationale": f"{dim}: {ev.get('rationale', '')}",
                    "tags": [dim, str(score)],
                })

        valid_scores = [s for s in scores.values() if isinstance(s, (int, float))]
        scores["mean"] = round(sum(valid_scores) / len(valid_scores), 3) if valid_scores else None
        scores["factor_means"] = {
            "cognitive_structural": _avg([scores.get(d) for d in ("COM", "SC")]),
            "affective_relational": _avg([scores.get(d) for d in ("AFF", "EIR", "EIM", "AGG")]),
            "self": _avg([scores.get(d) for d in ("SE", "ICS")]),
        }
        scores["narrative_summary"] = parsed.get("narrative_summary", "")

        return make_result(
            instrument=self.instrument_id,
            scores=scores,
            evidence=evidence,
            metadata=meta,
        )


def _avg(values: list) -> float | None:
    valid = [v for v in values if isinstance(v, (int, float))]
    return round(sum(valid) / len(valid), 3) if valid else None


register(SCORSGScorer())
