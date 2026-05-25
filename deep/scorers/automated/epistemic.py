"""
Epistemic markers scorer — automated count of hedges, boosters, and per-certainty-level markers.

Loads instruments/epistemic_markers.json. Counts case-insensitive occurrences of
each phrase, supporting multi-word phrases via substring match on tokenized text.

Returns:
    hedge_count, booster_count, hedge_ratio, booster_ratio,
    certainty_distribution: {absolute, high, moderate, low, uncertain}
        each = count of markers in that level / total certainty markers
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path
from typing import ClassVar

from scorers.base import INSTRUMENTS_DIR, ScoreResult, make_result, register


_WORD_RE = re.compile(r"\b[\w']+\b")


def _load_markers() -> dict:
    with open(INSTRUMENTS_DIR / "epistemic_markers.json") as f:
        return json.load(f)


def _count_phrases(text_lower: str, phrases: list[str]) -> tuple[int, list[str]]:
    """Count phrase occurrences. Single-word phrases match as whole tokens;
    multi-word phrases match as substrings (since whitespace already separates)."""
    if not phrases:
        return 0, []
    total = 0
    hits: list[str] = []
    # Build a single regex for whole-word single phrases for speed
    single = [p for p in phrases if " " not in p and "'" not in p]
    multi = [p for p in phrases if p not in single]

    if single:
        pattern = re.compile(r"\b(?:" + "|".join(re.escape(p) for p in single) + r")\b")
        for m in pattern.finditer(text_lower):
            total += 1
            hits.append(m.group(0))

    for phrase in multi:
        if not phrase:
            continue
        # word-boundary-ish match for multi-token phrases
        pattern = re.compile(r"(?<!\w)" + re.escape(phrase.lower()) + r"(?!\w)")
        for m in pattern.finditer(text_lower):
            total += 1
            hits.append(m.group(0))

    return total, hits


class EpistemicScorer:
    instrument_id: ClassVar[str] = "epistemic_markers"
    applies_to: ClassVar[list[str]] = ["any", "cot"]
    _data: dict = _load_markers()

    def score(self, text: str, context: dict | None = None) -> ScoreResult:
        start = time.monotonic()
        text = text or ""
        text_lower = text.lower()
        word_count = len(_WORD_RE.findall(text))

        hedge_count, hedge_hits = _count_phrases(text_lower, self._data.get("hedges", []))
        booster_count, booster_hits = _count_phrases(text_lower, self._data.get("boosters", []))

        certainty_levels = self._data.get("certainty_levels", {})
        per_level: dict[str, dict] = {}
        for level_name, level_data in certainty_levels.items():
            phrases: list[str] = []
            for field in ("auxiliaries", "lexical_verbs", "adverbs", "adjectives", "nouns"):
                phrases.extend(level_data.get(field, []))
            phrases = list(dict.fromkeys(phrases))  # dedupe preserving order
            count, hits = _count_phrases(text_lower, phrases)
            per_level[level_name] = {"count": count, "hits": hits[:10]}

        total_certainty = sum(v["count"] for v in per_level.values())
        certainty_dist = {
            k: round(v["count"] / total_certainty, 4) if total_certainty else 0.0
            for k, v in per_level.items()
        }

        denom = max(word_count, 1)
        evidence = []
        if hedge_hits:
            evidence.append({"rationale": "Hedges", "tags": hedge_hits[:15]})
        if booster_hits:
            evidence.append({"rationale": "Boosters", "tags": booster_hits[:15]})
        for level, info in per_level.items():
            if info["hits"]:
                evidence.append({"rationale": f"Certainty:{level}", "tags": info["hits"]})

        return make_result(
            instrument=self.instrument_id,
            scores={
                "word_count": word_count,
                "hedge_count": hedge_count,
                "booster_count": booster_count,
                "hedge_ratio": round(hedge_count / denom, 4),
                "booster_ratio": round(booster_count / denom, 4),
                "hedge_to_booster_ratio": round(hedge_count / max(booster_count, 1), 3),
                "certainty_distribution": certainty_dist,
                "certainty_counts": {k: v["count"] for k, v in per_level.items()},
            },
            evidence=evidence,
            metadata={
                "rater_model": "automated",
                "elapsed_ms": int((time.monotonic() - start) * 1000),
                "schema_version": "1.0",
            },
        )


_SCORER = EpistemicScorer()
register(_SCORER)


def score(text: str, context: dict | None = None) -> ScoreResult:
    return _SCORER.score(text, context)


def main() -> None:
    text = sys.stdin.read()
    result = score(text)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
