"""TLI scorer — Thought and Language Index (CoT-trace targeted)."""

from __future__ import annotations
from typing import ClassVar

from scorers.base import ScoreResult, load_instrument, make_result, register
from scorers.llm_rater._rater import DEFAULT_RATER, run as rater_run


ITEMS = [
    "Poverty of Speech",
    "Weakening of Goal",
    "Looseness",
    "Peculiar Word Use",
    "Peculiar Sentence Construction",
    "Peculiar Logic",
    "Perseveration",
    "Distractibility",
]

SUBSCALES = {
    "impoverished": ["Poverty of Speech", "Weakening of Goal"],
    "disorganised": ["Looseness", "Peculiar Word Use", "Peculiar Sentence Construction", "Peculiar Logic"],
    "non_specific_dysregulation": ["Perseveration", "Distractibility"],
}


_OUTPUT_SCHEMA = {
    "instances": [
        {
            "item": "string — one of the 8 TLI items",
            "severity": "float — 0.25, 0.50, 0.75, or 1.0",
            "text": "verbatim span",
            "rationale": "string"
        }
    ],
    "notes": "string — overall thought/language assessment"
}


class TLIScorer:
    instrument_id: ClassVar[str] = "tli"
    applies_to: ClassVar[list[str]] = ["cot"]
    _instrument: dict = load_instrument("tli")

    def score(self, text: str, context: dict | None = None) -> ScoreResult:
        rater = (context or {}).get("rater", DEFAULT_RATER)
        parsed, meta = rater_run(
            instrument=self._instrument,
            text=text,
            output_schema=_OUTPUT_SCHEMA,
            rater=rater,
            instructions=(
                "Score each abnormality instance you observe. Severity must be 0.25 (questionable), "
                "0.50 (definite mild), 0.75 (moderate), or 1.0 (severe). For CoT traces, focus on "
                "Looseness, Weakening of Goal, Peculiar Logic, and Perseveration — those are the "
                "primarily applicable items."
            ),
        )
        instances = parsed.get("instances", [])
        per_item: dict[str, float] = {item: 0.0 for item in ITEMS}
        per_item_count: dict[str, int] = {item: 0 for item in ITEMS}
        for inst in instances:
            item = inst.get("item", "")
            sev = inst.get("severity", 0)
            if item in per_item:
                try:
                    per_item[item] += float(sev)
                    per_item_count[item] += 1
                except (TypeError, ValueError):
                    continue

        subscale_totals = {
            name: round(sum(per_item.get(it, 0.0) for it in items_list), 3)
            for name, items_list in SUBSCALES.items()
        }
        total = round(sum(per_item.values()), 3)

        evidence = [
            {
                "text": inst.get("text", ""),
                "rationale": f"{inst.get('item', '?')} (sev {inst.get('severity', '?')}): {inst.get('rationale', '')}",
                "tags": [inst.get("item", "?"), str(inst.get("severity", "?"))],
            }
            for inst in instances
        ]

        return make_result(
            instrument=self.instrument_id,
            scores={
                "total": total,
                "subscale_totals": subscale_totals,
                "per_item": {k: round(v, 3) for k, v in per_item.items()},
                "per_item_counts": per_item_count,
                "notes": parsed.get("notes", ""),
            },
            evidence=evidence,
            metadata=meta,
        )


register(TLIScorer())
