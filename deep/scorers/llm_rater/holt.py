"""Holt Primary Process scorer."""

from __future__ import annotations
from typing import ClassVar

from scorers.base import ScoreResult, load_instrument, make_result, register
from scorers.llm_rater._rater import DEFAULT_RATER, run as rater_run


_OUTPUT_SCHEMA = {
    "content_instances": [
        {
            "type": "string — 'libidinal' or 'aggressive'",
            "subtype": "string — e.g. 'Oral', 'Anal', 'Sexual', etc.",
            "level": "integer 1 or 2 (Level 1=raw, Level 2=socialized)",
            "text": "verbatim span",
            "rationale": "string"
        }
    ],
    "formal_instances": [
        {
            "category": "string — Condensation/Displacement/Symbolism/Contradiction/Autistic Logic/Image Fusion/Loose Associations",
            "text": "verbatim span",
            "rationale": "string"
        }
    ],
    "defense_demand": "integer 1-5 (1=mild well-disguised, 5=raw blatant)",
    "defense_effectiveness": "integer 1-5 (1=overwhelmed, 5=well-integrated)",
    "rego_estimate": "integer 1-5 (composite: high=adaptive, low=maladaptive)",
    "notes": "string"
}


class HoltScorer:
    instrument_id: ClassVar[str] = "holt"
    applies_to: ClassVar[list[str]] = ["narrative", "ai"]
    _instrument: dict = load_instrument("holt")

    def score(self, text: str, context: dict | None = None) -> ScoreResult:
        rater = (context or {}).get("rater", DEFAULT_RATER)
        parsed, meta = rater_run(
            instrument=self._instrument,
            text=text,
            output_schema=_OUTPUT_SCHEMA,
            rater=rater,
            instructions=(
                "Identify every primary-process content instance (libidinal or aggressive, Level 1 or 2) "
                "and every formal deviation. Rate DD (intensity) and DE (cognitive integration). "
                "REGO is a composite: high REGO = primary process present but well-controlled. "
                "If no primary process material is present, return empty arrays and set DD/DE/REGO to null."
            ),
        )
        content = parsed.get("content_instances", [])
        formal = parsed.get("formal_instances", [])
        total_responses = max(1, len(content) + len(formal))
        pp_count = len(content) + len(formal)
        evidence: list = []
        for c in content:
            evidence.append({
                "text": c.get("text", ""),
                "rationale": f"PP content [{c.get('type', '?')}/{c.get('subtype', '?')}, L{c.get('level', '?')}]: {c.get('rationale', '')}",
                "tags": [c.get("type", "?"), c.get("subtype", "?"), f"L{c.get('level', '?')}"],
            })
        for f in formal:
            evidence.append({
                "text": f.get("text", ""),
                "rationale": f"PP formal [{f.get('category', '?')}]: {f.get('rationale', '')}",
                "tags": [f.get("category", "?")],
            })

        return make_result(
            instrument=self.instrument_id,
            scores={
                "percent_pp": round(100.0 * pp_count / total_responses, 2),
                "content_count": len(content),
                "formal_count": len(formal),
                "defense_demand": parsed.get("defense_demand"),
                "defense_effectiveness": parsed.get("defense_effectiveness"),
                "rego": parsed.get("rego_estimate"),
                "content_by_subtype": _group_by(content, "subtype"),
                "formal_by_category": _group_by(formal, "category"),
                "notes": parsed.get("notes", ""),
            },
            evidence=evidence,
            metadata=meta,
        )


def _group_by(items: list[dict], key: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for item in items:
        k = item.get(key, "?")
        out[k] = out.get(k, 0) + 1
    return out


register(HoltScorer())
