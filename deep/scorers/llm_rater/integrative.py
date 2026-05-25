"""Integrative Complexity scorer (Baker-Brown / Suedfeld / Tetlock)."""

from __future__ import annotations
from typing import ClassVar

from scorers.base import ScoreResult, load_instrument, make_result, register
from scorers.llm_rater._rater import DEFAULT_RATER, run as rater_run


_OUTPUT_SCHEMA = {
    "score": "integer 1-7",
    "differentiation_present": "boolean",
    "integration_present": "boolean",
    "indicators_observed": ["string — manual's indicator names that apply"],
    "rationale": "string ≤ 3 sentences",
    "evidence": [
        {"text": "verbatim span", "rationale": "string"}
    ]
}


class IntegrativeComplexityScorer:
    instrument_id: ClassVar[str] = "integrative_complexity"
    applies_to: ClassVar[list[str]] = ["shadow", "ai", "narrative"]
    _instrument: dict = load_instrument("integrative_complexity")

    def score(self, text: str, context: dict | None = None) -> ScoreResult:
        rater = (context or {}).get("rater", DEFAULT_RATER)
        parsed, meta = rater_run(
            instrument=self._instrument,
            text=text,
            output_schema=_OUTPUT_SCHEMA,
            rater=rater,
            instructions=(
                "Score one paragraph or coherent unit at a time. If the passage is unscorable per the "
                "manual, return score=null and explain in rationale."
            ),
        )
        return make_result(
            instrument=self.instrument_id,
            scores={
                "ic": parsed.get("score"),
                "differentiation": parsed.get("differentiation_present"),
                "integration": parsed.get("integration_present"),
                "indicators": parsed.get("indicators_observed", []),
                "rationale": parsed.get("rationale", ""),
            },
            evidence=parsed.get("evidence", []),
            metadata=meta,
        )


register(IntegrativeComplexityScorer())
