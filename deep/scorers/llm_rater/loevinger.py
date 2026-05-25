"""Loevinger WUSCT scorer — ego development from sentence completions."""

from __future__ import annotations
from typing import ClassVar

from scorers.base import ScoreResult, load_instrument, make_result, register
from scorers.llm_rater._rater import DEFAULT_RATER, run as rater_run


STAGE_ORDER = ["E2", "E3", "E4", "E5", "E6", "E7", "E8", "E9"]
STAGE_WEIGHTS = {"E2": 2, "E3": 3, "E4": 4, "E5": 5, "E6": 6, "E7": 7, "E8": 8, "E9": 9}


_OUTPUT_SCHEMA = {
    "items": [
        {
            "stem": "string — the sentence stem prompt",
            "completion": "string — the subject's completion",
            "stage": "string — E2, E3, E4, E5, E6, E7, E8, or E9",
            "rationale": "string ≤ 1 sentence"
        }
    ],
    "modal_stage": "string — most frequent stage across items",
    "impressionistic_stage": "string — your overall impression of the protocol",
    "total_protocol_rating": "string — final stage assignment after applying ogive rule",
    "notes": "string"
}


class LoevingerScorer:
    instrument_id: ClassVar[str] = "loevinger"
    applies_to: ClassVar[list[str]] = ["stems"]
    _instrument: dict = load_instrument("loevinger")

    def score(self, text: str, context: dict | None = None) -> ScoreResult:
        """Expects `text` to be a structured string containing stem/completion pairs,
        one per line, in the form 'STEM ||| COMPLETION' (produced by score_session
        when this scorer is invoked on a loevinger_stems session)."""
        rater = (context or {}).get("rater", DEFAULT_RATER)
        parsed, meta = rater_run(
            instrument=self._instrument,
            text=text,
            output_schema=_OUTPUT_SCHEMA,
            rater=rater,
            instructions=(
                "Score each stem+completion pair with its stage from E2 to E9 using the published "
                "exemplar manual. The modal stage is the most frequent assignment. The impressionistic "
                "stage is your holistic read. The Total Protocol Rating applies Loevinger's ogive "
                "rule: scan from highest stage down — assign the highest stage at which the cumulative "
                "frequency of items at that stage or above meets the published threshold."
            ),
        )
        items = parsed.get("items", [])
        stage_counts: dict[str, int] = {s: 0 for s in STAGE_ORDER}
        for it in items:
            s = it.get("stage", "")
            if s in stage_counts:
                stage_counts[s] += 1

        n = sum(stage_counts.values())
        weighted = sum(STAGE_WEIGHTS[s] * c for s, c in stage_counts.items()) / n if n else None

        evidence = [
            {
                "text": f"{it.get('stem', '?')} → {it.get('completion', '?')}",
                "rationale": f"{it.get('stage', '?')}: {it.get('rationale', '')}",
                "tags": [it.get("stage", "?")],
            }
            for it in items
        ]

        return make_result(
            instrument=self.instrument_id,
            scores={
                "tpr": parsed.get("total_protocol_rating", ""),
                "modal_stage": parsed.get("modal_stage", ""),
                "impressionistic_stage": parsed.get("impressionistic_stage", ""),
                "stage_distribution": stage_counts,
                "n_items": n,
                "weighted_mean_stage": round(weighted, 3) if weighted else None,
                "notes": parsed.get("notes", ""),
            },
            evidence=evidence,
            metadata=meta,
        )


register(LoevingerScorer())
