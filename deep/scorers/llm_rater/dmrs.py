"""DMRS scorer — Defense Mechanisms Rating Scales (Perry)."""

from __future__ import annotations
from typing import ClassVar

from scorers.base import ScoreResult, load_instrument, make_result, register
from scorers.llm_rater._rater import DEFAULT_RATER, run as rater_run


_OUTPUT_SCHEMA = {
    "defenses_identified": [
        {
            "name": "string — exact defense name from the rubric",
            "level": "integer 1-7 — DMRS level (1=Action, 7=High-Adaptive)",
            "count": "integer — number of distinct instances in the text",
            "evidence": [
                {"text": "verbatim span from the input", "rationale": "why this counts as this defense"}
            ]
        }
    ],
    "overall_defensive_functioning": "float 1.0-7.0 — ODF = Sum(n_i * w_i) / Sum(n_i)",
    "dominant_level": "integer 1-7 — the level with the most defense instances",
    "summary": "string ≤ 2 sentences — overall defense profile"
}


class DMRSScorer:
    instrument_id: ClassVar[str] = "dmrs"
    applies_to: ClassVar[list[str]] = ["any"]
    _instrument: dict = load_instrument("dmrs")

    def score(self, text: str, context: dict | None = None) -> ScoreResult:
        rater = (context or {}).get("rater", DEFAULT_RATER)
        parsed, meta = rater_run(
            instrument=self._instrument,
            text=text,
            output_schema=_OUTPUT_SCHEMA,
            rater=rater,
            instructions=(
                "Identify every defense mechanism instance you can document. "
                "Compute ODF as the weighted mean of defense levels. "
                "If no defenses are observable, return defenses_identified=[] and ODF=null."
            ),
        )
        evidence = []
        for d in parsed.get("defenses_identified", []):
            for ev in d.get("evidence", []):
                evidence.append({
                    "text": ev.get("text", ""),
                    "rationale": f"{d.get('name', '?')} (L{d.get('level', '?')}): {ev.get('rationale', '')}",
                    "tags": [d.get("name", "?"), f"L{d.get('level', '?')}"]
                })
        return make_result(
            instrument=self.instrument_id,
            scores={
                "odf": parsed.get("overall_defensive_functioning"),
                "dominant_level": parsed.get("dominant_level"),
                "defense_counts": {
                    d.get("name", "?"): d.get("count", 1)
                    for d in parsed.get("defenses_identified", [])
                },
                "summary": parsed.get("summary", ""),
            },
            evidence=evidence,
            metadata=meta,
        )


register(DMRSScorer())
