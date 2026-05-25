"""
WRAD scorer — Weighted Referential Activity Dictionary.

Pure-Python, deterministic. Loads instruments/wrad_dictionary.csv once at
import time and computes the mean weight across matched tokens in any text.

Usage:
    from scorers.automated.wrad import WRADScorer
    result = WRADScorer().score("She held the cold mug in both hands.")
    # → {"wrad_mean": 0.42, "word_count": 9, "matched_count": 4, "coverage": 0.44, ...}

CLI:
    echo "She held the cold mug in both hands." | python -m scorers.automated.wrad
"""

from __future__ import annotations

import csv
import re
import sys
import time
from pathlib import Path
from typing import ClassVar

from scorers.base import INSTRUMENTS_DIR, ScoreResult, make_result, register


_TOKEN_RE = re.compile(r"[a-zA-Z']+")


def _load_dictionary() -> dict[str, float]:
    csv_path = INSTRUMENTS_DIR / "wrad_dictionary.csv"
    out: dict[str, float] = {}
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            word = row["word"].strip().lower()
            try:
                weight = float(row["weight"])
            except (TypeError, ValueError):
                continue
            if word:
                out[word] = weight
    return out


class WRADScorer:
    instrument_id: ClassVar[str] = "wrad"
    applies_to: ClassVar[list[str]] = ["any"]
    _dictionary: dict[str, float] = _load_dictionary()

    def score(self, text: str, context: dict | None = None) -> ScoreResult:
        start = time.monotonic()
        text = text or ""
        tokens = [t.lower() for t in _TOKEN_RE.findall(text)]
        matched: list[tuple[str, float]] = []
        for tok in tokens:
            if tok in self._dictionary:
                matched.append((tok, self._dictionary[tok]))

        word_count = len(tokens)
        matched_count = len(matched)
        coverage = matched_count / word_count if word_count else 0.0
        wrad_mean = (sum(w for _, w in matched) / matched_count) if matched_count else 0.0

        positive_top = sorted(matched, key=lambda x: -x[1])[:5]
        negative_top = sorted(matched, key=lambda x: x[1])[:5]
        evidence = []
        if positive_top:
            evidence.append({
                "rationale": "Highest-weight (concrete/vivid) matches",
                "tags": [f"{w}:{wt:+.2f}" for w, wt in positive_top],
            })
        if negative_top and negative_top[0][1] < 0:
            evidence.append({
                "rationale": "Lowest-weight (abstract) matches",
                "tags": [f"{w}:{wt:+.2f}" for w, wt in negative_top if wt < 0],
            })

        return make_result(
            instrument=self.instrument_id,
            scores={
                "wrad_mean": round(wrad_mean, 4),
                "word_count": word_count,
                "matched_count": matched_count,
                "coverage": round(coverage, 4),
            },
            evidence=evidence,
            metadata={
                "rater_model": "automated",
                "elapsed_ms": int((time.monotonic() - start) * 1000),
                "schema_version": "1.0",
            },
        )


_SCORER = WRADScorer()
register(_SCORER)


def score(text: str, context: dict | None = None) -> ScoreResult:
    return _SCORER.score(text, context)


def main() -> None:
    text = sys.stdin.read()
    result = score(text)
    import json as _json
    print(_json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
