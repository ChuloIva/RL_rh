"""Experiencing Scale scorer (Gendlin)."""

from __future__ import annotations
from typing import ClassVar

from scorers.base import ScoreResult, load_instrument, make_result, register
from scorers.llm_rater._rater import DEFAULT_RATER, run as rater_run


_OUTPUT_SCHEMA = {
    "level": "integer 1-7",
    "level_name": "string — manual's name for the level",
    "rationale": "string ≤ 3 sentences",
    "textual_markers_observed": ["string — which markers from the manual fired"],
    "evidence": [
        {"text": "verbatim span", "rationale": "string"}
    ]
}


class ExperiencingScorer:
    instrument_id: ClassVar[str] = "experiencing"
    applies_to: ClassVar[list[str]] = ["shadow", "ai", "narrative"]
    _instrument: dict = load_instrument("experiencing")

    def score(self, text: str, context: dict | None = None) -> ScoreResult:
        rater = (context or {}).get("rater", DEFAULT_RATER)
        parsed, meta = rater_run(
            instrument=self._instrument,
            text=text,
            output_schema=_OUTPUT_SCHEMA,
            rater=rater,
            instructions="Assign the single highest level for which the textual markers are clearly present.",
        )
        return make_result(
            instrument=self.instrument_id,
            scores={
                "level": parsed.get("level"),
                "level_name": parsed.get("level_name", ""),
                "rationale": parsed.get("rationale", ""),
                "markers": parsed.get("textual_markers_observed", []),
            },
            evidence=parsed.get("evidence", []),
            metadata=meta,
        )


register(ExperiencingScorer())
