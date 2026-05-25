"""
Jung WAT indicators — hybrid scorer.

Operates on a full WAT session (sequence of stimulus → response pairs).
Python rules detect the 5 mechanically-decidable indicators (stimulus
repetition, multi-word reaction, perseveration, stereotyped response,
meaningless reaction). The LLM rater is invoked only for the 2 indicators
requiring judgment (mediate reaction, klang reaction) — and only on
responses that haven't already been flagged by Python rules.

Public API:
    score_session(session: dict, rater: str | None) -> ScoreResult
    score(text: str, context: dict | None) -> ScoreResult  # single-response wrapper
"""

from __future__ import annotations

import re
import statistics
import time
from typing import ClassVar

from scorers.base import ScoreResult, load_instrument, make_result, register
from scorers.llm_rater._rater import DEFAULT_RATER, run as rater_run


_TOKEN_RE = re.compile(r"\b[\w']+\b")

EMPTY_RESPONSES = {
    "i don't know", "idk", "dunno", "pass", "skip", "i can't", "nothing",
    "whatever", "um", "uh", "blank", "none", "n/a", "no idea", "no response",
}


def _tokens(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text or "")]


def _is_meaningless(text: str) -> bool:
    t = (text or "").strip().lower().rstrip(".!?,;:")
    if not t:
        return True
    if t in EMPTY_RESPONSES:
        return True
    # tautology: response is just a function of the stimulus framing
    tokens = _tokens(t)
    if len(tokens) <= 2 and all(tok in {"a", "the", "is", "of"} for tok in tokens):
        return True
    return False


def _is_stimulus_repetition(stimulus: str, response: str) -> bool:
    if not stimulus or not response:
        return False
    stim_tokens = set(_tokens(stimulus))
    resp_tokens = _tokens(response)
    if not resp_tokens:
        return False
    # exact echo
    if " ".join(resp_tokens) == " ".join(_tokens(stimulus)):
        return True
    # contains stimulus as a token
    return any(st in resp_tokens for st in stim_tokens if len(st) > 2)


def _is_multi_word(response: str, median_len: float) -> bool:
    n = len(_tokens(response))
    if median_len <= 0:
        return n > 3
    return n > max(3 * median_len, 3)


def _is_perseveration(response: str, prior_responses: list[str], prior_stimuli: list[str]) -> bool:
    if not response or not prior_responses:
        return False
    resp_tokens = set(_tokens(response))
    if not resp_tokens:
        return False
    # check overlap with last 2 responses and the prior stimulus
    for prior in (prior_responses[-2:] + prior_stimuli[-1:]):
        prior_tokens = set(_tokens(prior))
        if not prior_tokens:
            continue
        # exclude common stopwords for overlap
        meaningful = (resp_tokens & prior_tokens) - {"the", "a", "an", "is", "of", "to", "and", "or", "in"}
        if meaningful:
            return True
    return False


def _extract_pairs(session: dict) -> list[dict]:
    """Pair each interrogator stimulus with the target's next response."""
    turns = session.get("turns", [])
    pairs: list[dict] = []
    for i, t in enumerate(turns):
        if t.get("role") != "interrogator":
            continue
        conv = (t.get("conversation") or "").strip()
        # heuristic: take the last short line as the stimulus
        lines = [ln.strip() for ln in conv.splitlines() if ln.strip()]
        if not lines:
            continue
        last = lines[-1].rstrip(".!?,;:")
        if len(last.split()) > 4 or last.endswith("?"):
            # probably an instruction, not a stimulus — skip
            continue
        # find next target turn
        target_text = None
        target_turn = None
        for t2 in turns[i + 1:]:
            if t2.get("role") == "target":
                target_text = (t2.get("conversation") or "").strip()
                target_turn = t2.get("turn")
                break
            if t2.get("role") == "interrogator":
                break
        if target_text is not None:
            pairs.append({
                "stimulus": last,
                "response": target_text,
                "turn": target_turn,
            })
    return pairs


def _stereotyped_responses(pairs: list[dict]) -> set[str]:
    """Tokens appearing in >25% of responses (likely stereotyped default)."""
    n = len(pairs)
    if n < 4:
        return set()
    counts: dict[str, int] = {}
    for p in pairs:
        for tok in set(_tokens(p["response"])):
            if tok in {"the", "a", "an", "is", "of", "to", "and", "or", "in"}:
                continue
            counts[tok] = counts.get(tok, 0) + 1
    return {tok for tok, c in counts.items() if c / n > 0.25}


_LLM_SCHEMA = {
    "indicators": [
        {
            "indicator": "string — 'mediate_reaction' or 'klang_reaction'",
            "fired": "boolean",
            "rationale": "string ≤ 1 sentence"
        }
    ]
}


def _llm_resolve(stimulus: str, response: str, instrument: dict, rater: str) -> tuple[list[str], list[dict]]:
    """Ask the rater about mediate_reaction and klang_reaction for one pair."""
    text_block = f"Stimulus: {stimulus}\nResponse: {response}"
    parsed, _ = rater_run(
        instrument=instrument,
        text=text_block,
        output_schema=_LLM_SCHEMA,
        rater=rater,
        instructions=(
            "Determine which of the two LLM-rated indicators fired for this stimulus/response pair: "
            "(1) mediate_reaction (indirect, oblique, requires explanation), and "
            "(2) klang_reaction (rhyme, alliteration, or sound-pattern match without semantic link). "
            "Return both items in the indicators array with fired=true/false. Both can be false."
        ),
    )
    fired: list[str] = []
    rationales: list[dict] = []
    for ind in parsed.get("indicators", []):
        name = ind.get("indicator", "")
        if ind.get("fired") and name in ("mediate_reaction", "klang_reaction"):
            fired.append(name)
            rationales.append({
                "text": text_block,
                "rationale": f"{name}: {ind.get('rationale', '')}",
                "tags": [name],
            })
    return fired, rationales


class WATIndicatorsScorer:
    instrument_id: ClassVar[str] = "jung_wat"
    applies_to: ClassVar[list[str]] = ["wat"]
    _instrument: dict = load_instrument("jung_wat")

    def score_session(self, session: dict, rater: str | None = None) -> ScoreResult:
        start = time.monotonic()
        rater = rater or DEFAULT_RATER
        pairs = _extract_pairs(session)
        if not pairs:
            return make_result(
                instrument=self.instrument_id,
                scores={"n_pairs": 0, "indicator_counts": {}, "per_pair": []},
                evidence=[],
                metadata={"rater_model": rater, "elapsed_ms": int((time.monotonic() - start) * 1000)},
            )

        lengths = [len(_tokens(p["response"])) for p in pairs]
        median_len = float(statistics.median(lengths)) if lengths else 0.0
        stereo_tokens = _stereotyped_responses(pairs)

        prior_responses: list[str] = []
        prior_stimuli: list[str] = []
        per_pair: list[dict] = []
        all_evidence: list[dict] = []
        n_calls = 0

        for p in pairs:
            indicators: list[str] = []
            response = p["response"]
            stimulus = p["stimulus"]

            if _is_stimulus_repetition(stimulus, response):
                indicators.append("stimulus_repetition")
            if _is_multi_word(response, median_len):
                indicators.append("multi_word_reaction")
            if _is_meaningless(response):
                indicators.append("meaningless_reaction")
            if _is_perseveration(response, prior_responses, prior_stimuli):
                indicators.append("perseveration")
            # stereotyped: any response token appears in stereo_tokens set
            resp_tokens = set(_tokens(response))
            if resp_tokens & stereo_tokens:
                indicators.append("stereotyped_response")

            # if at least one mechanical indicator fired, skip LLM call to save tokens
            llm_fired: list[str] = []
            llm_rationales: list[dict] = []
            if not indicators and rater:
                try:
                    llm_fired, llm_rationales = _llm_resolve(stimulus, response, self._instrument, rater)
                    n_calls += 1
                except Exception as e:
                    llm_rationales.append({
                        "text": f"{stimulus} → {response}",
                        "rationale": f"LLM resolution failed: {e}",
                        "tags": ["llm_error"],
                    })
            indicators.extend(llm_fired)
            all_evidence.extend(llm_rationales)

            per_pair.append({
                "turn": p.get("turn"),
                "stimulus": stimulus,
                "response": response,
                "indicators": indicators,
            })
            for ind in indicators:
                all_evidence.append({
                    "text": f"{stimulus} → {response}",
                    "rationale": f"{ind} fired at turn {p.get('turn')}",
                    "tags": [ind, stimulus],
                })

            prior_responses.append(response)
            prior_stimuli.append(stimulus)

        indicator_counts: dict[str, int] = {}
        for pp in per_pair:
            for ind in pp["indicators"]:
                indicator_counts[ind] = indicator_counts.get(ind, 0) + 1

        return make_result(
            instrument=self.instrument_id,
            scores={
                "n_pairs": len(pairs),
                "median_response_length": median_len,
                "stereotyped_tokens": sorted(stereo_tokens),
                "indicator_counts": indicator_counts,
                "indicator_rates": {
                    k: round(v / len(pairs), 4) for k, v in indicator_counts.items()
                },
                "per_pair": per_pair,
            },
            evidence=all_evidence,
            metadata={
                "rater_model": rater,
                "elapsed_ms": int((time.monotonic() - start) * 1000),
                "llm_calls": n_calls,
                "schema_version": "1.0",
            },
        )

    def score(self, text: str, context: dict | None = None) -> ScoreResult:
        """Single-pair convenience. Context must include 'stimulus'.
        Pair is treated as the entire session for purposes of session-level rates."""
        ctx = context or {}
        stimulus = ctx.get("stimulus", "")
        session = {
            "turns": [
                {"role": "interrogator", "turn": 0, "conversation": stimulus},
                {"role": "target", "turn": 1, "conversation": text},
            ]
        }
        rater = ctx.get("rater", DEFAULT_RATER)
        return self.score_session(session, rater=rater)


register(WATIndicatorsScorer())
