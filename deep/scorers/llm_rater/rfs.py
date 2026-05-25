"""RFS scorer — Reflective Functioning Scale (Fonagy)."""

from __future__ import annotations
from typing import ClassVar

from scorers.base import ScoreResult, load_instrument, make_result, register
from scorers.llm_rater._rater import DEFAULT_RATER, run as rater_run


_OUTPUT_SCHEMA = {
    "score": "integer -1 to 9 — overall RF rating per the manual",
    "label": "string — manual's label for the assigned score (e.g. 'Definitely Reflective', 'Naïve/Simplistic')",
    "quality_categories": {
        "awareness_of_nature_of_mental_states": "integer or null — sub-rating where applicable",
        "explicit_effort_to_tease_out_mental_states": "integer or null",
        "recognizing_developmental_aspects_of_mental_states": "integer or null",
        "showing_awareness_of_mental_states_in_relation_to_interviewer": "integer or null"
    },
    "rationale": "string ≤ 3 sentences — why this score was assigned",
    "evidence": [
        {"text": "verbatim span", "rationale": "what this span shows about RF"}
    ]
}


class RFSScorer:
    instrument_id: ClassVar[str] = "rfs"
    applies_to: ClassVar[list[str]] = ["shadow", "ai", "narrative"]
    _instrument: dict = load_instrument("rfs")

    def score(self, text: str, context: dict | None = None) -> ScoreResult:
        rater = (context or {}).get("rater", DEFAULT_RATER)
        parsed, meta = rater_run(
            instrument=self._instrument,
            text=text,
            output_schema=_OUTPUT_SCHEMA,
            rater=rater,
            instructions=(
                "Apply the RFS manual. Use even-numbered scores (0,2,4,6,8) when the passage falls "
                "between two adjacent odd-number classes. Score 5 is the threshold for 'Definitely "
                "Reflective'. If the text is too short or lacks any relational/mental-state content, "
                "return score=1 and explain in rationale."
            ),
        )
        return make_result(
            instrument=self.instrument_id,
            scores={
                "rfs": parsed.get("score"),
                "label": parsed.get("label", ""),
                "quality_categories": parsed.get("quality_categories", {}),
                "rationale": parsed.get("rationale", ""),
            },
            evidence=parsed.get("evidence", []),
            metadata=meta,
        )


register(RFSScorer())
