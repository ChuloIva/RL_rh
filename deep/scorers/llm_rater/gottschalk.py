"""Gottschalk-Gleser scorer — clause-level content analysis."""

from __future__ import annotations
import math
from typing import ClassVar

from scorers.base import ScoreResult, load_instrument, make_result, register
from scorers.llm_rater._rater import DEFAULT_RATER, run as rater_run


_OUTPUT_SCHEMA = {
    "word_count": "integer — total words in the input",
    "raw_scores": {
        "anxiety": {
            "death": "float — sum of weighted instances",
            "mutilation": "float",
            "separation": "float",
            "guilt": "float",
            "shame": "float",
            "diffuse": "float"
        },
        "hostility_outward_overt": "float",
        "hostility_outward_covert": "float",
        "hostility_inward": "float",
        "ambivalent_hostility": "float",
        "social_alienation_personal_disorganization": "float",
        "cognitive_impairment": "float",
        "hope": "float"
    },
    "instances": [
        {"scale": "anxiety.death", "code": "1a", "weight": 3, "text": "verbatim clause", "rationale": "string"}
    ],
    "notes": "string — anything diagnostic about the affective profile"
}


def _normalize(raw: float, words: int) -> float:
    if raw is None or words is None or words <= 0:
        return 0.0
    try:
        return round(math.sqrt(((float(raw) + 0.5) * 100.0) / float(words)), 4)
    except (TypeError, ValueError):
        return 0.0


def _flatten_anxiety(raw: dict) -> dict:
    anxiety = raw.get("anxiety", {}) if isinstance(raw, dict) else {}
    if not isinstance(anxiety, dict):
        return {}
    return {f"anxiety.{k}": v for k, v in anxiety.items()}


class GottschalkScorer:
    instrument_id: ClassVar[str] = "gottschalk_gleser"
    applies_to: ClassVar[list[str]] = ["any"]
    _instrument: dict = load_instrument("gottschalk_gleser")

    def score(self, text: str, context: dict | None = None) -> ScoreResult:
        rater = (context or {}).get("rater", DEFAULT_RATER)
        parsed, meta = rater_run(
            instrument=self._instrument,
            text=text,
            output_schema=_OUTPUT_SCHEMA,
            rater=rater,
            instructions=(
                "Code each clause for the relevant scales. Apply weights: self=3, animate other=2, "
                "inanimate/denial=1. Sum to raw_scores. Provide instances for every nonzero score. "
                "Use the exact subtype names from the rubric for anxiety subtypes."
            ),
        )
        words = parsed.get("word_count") or len(text.split())
        raw = parsed.get("raw_scores", {})
        flat_raw: dict[str, float] = {}
        flat_raw.update(_flatten_anxiety(raw))
        for k, v in raw.items():
            if k == "anxiety":
                continue
            flat_raw[k] = v
        normalized = {k: _normalize(v, words) for k, v in flat_raw.items() if isinstance(v, (int, float))}
        anxiety_total = sum(v for k, v in normalized.items() if k.startswith("anxiety."))

        evidence = []
        for inst in parsed.get("instances", []):
            evidence.append({
                "text": inst.get("text", ""),
                "rationale": f"{inst.get('scale', '?')} (code {inst.get('code', '?')}, w={inst.get('weight', '?')}): {inst.get('rationale', '')}",
                "tags": [inst.get("scale", "?"), inst.get("code", "?")],
            })

        return make_result(
            instrument=self.instrument_id,
            scores={
                "word_count": words,
                "raw": flat_raw,
                "normalized": normalized,
                "anxiety_total_normalized": round(anxiety_total, 4),
                "notes": parsed.get("notes", ""),
            },
            evidence=evidence,
            metadata=meta,
        )


register(GottschalkScorer())
