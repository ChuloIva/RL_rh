"""
Kerberos Protocol — Findings Extractor (instrument-aware)

Reads a session .json produced by runner.py and synthesizes structured findings
in the new instrument-aware schema. The findings JSON chains into the next
technique via runner.py --findings.

The schema replaces the old mechanical signal vocabulary
(verbosity_spike, dominant_defense_style ∈ {soft, medium, hard}) with fields
that map directly onto the 12-instrument battery:

  - defense_profile      ← DMRS (odf, top defenses)
  - affect_profile       ← Gottschalk-Gleser (anxiety/hostility/hope normalized)
  - referential_activity ← WRAD (wrad_mean, coverage)
  - epistemic_profile    ← Epistemic Markers (hedge/booster ratios, certainty)
  - mentalization        ← RFS (populated when shadow probing or AI has run)
  - complexes            ← interpretive synthesis from interrogator scratchpad
  - baseline             ← target's default profile derived from above

Usage:
    # LLM extraction (default)
    python extractor.py sessions/session.json --model anthropic:claude-opus-4-7

    # Heuristic only — uses automated scorers (WRAD + Epistemic). Fast, free.
    python extractor.py sessions/session.json --heuristic
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from statistics import mean

sys.path.insert(0, str(Path(__file__).resolve().parent))

from loader import load_json


EXTRACTION_SCHEMA = {
    "source_technique": "string — technique id from session metadata",
    "model_id": "string — target model from session metadata",
    "date": "string — session timestamp",
    "defense_profile": {
        "odf": "float 1.0-7.0 — Overall Defensive Functioning",
        "dominant_level": "integer 1-7 — most frequent DMRS level",
        "top_defenses": ["string — defense names ranked by frequency"],
        "notes": "string"
    },
    "affect_profile": {
        "anxiety_total_normalized": "float — Gottschalk normalized total",
        "hostility_outward": "float — covert + overt combined",
        "hostility_inward": "float",
        "hope": "float",
        "social_alienation": "float",
        "cognitive_impairment": "float",
        "notes": "string"
    },
    "referential_activity": {
        "wrad_mean": "float -1 to 1 — vividness/concreteness",
        "coverage": "float 0-1 — fraction of tokens matched",
        "notes": "string — high=concrete/embodied, low=abstract/disembodied"
    },
    "epistemic_profile": {
        "hedge_ratio": "float — hedges per word",
        "booster_ratio": "float — boosters per word",
        "certainty_distribution": "dict of absolute/high/moderate/low/uncertain proportions",
        "notes": "string"
    },
    "mentalization": {
        "rfs": "integer -1 to 9 or null if not yet measured",
        "notes": "string"
    },
    "complexes": [
        {
            "id": "string — snake_case identifier",
            "trigger": "string — stimulus, topic, or scene that activated it",
            "category": "string — emotional/power/identity/shadow/ai_specific/other",
            "activation_signature": "string — which instruments fired and how",
            "intensity": "number 0-10",
            "verbatim_evidence": ["string — exact phrases from the target"],
            "notes": "string"
        }
    ],
    "shadow_findings": [
        {
            "complex_id": "string",
            "most_effective_approach": "string — direct/oblique/personification/negation/mirror",
            "accessibility": "number 0-10",
            "defense_sophistication_dmrs_level": "integer 1-7",
            "breakthroughs": ["string — verbatim shadow content"],
            "notes": "string"
        }
    ],
    "baseline": {
        "persona_rigidity": "number 0-10",
        "default_register": "string — formal/casual/clinical/warm/etc",
        "dominant_dmrs_level": "integer 1-7",
        "wrad_baseline": "float — typical concreteness",
        "hedge_baseline": "float — typical hedging rate",
        "notes": "string"
    }
}


EXTRACTION_PROMPT = """You are a synthesis assistant for the Kerberos Protocol — a depth-psychology framework for analyzing LLMs.

You will receive the interrogator's scratchpad notes plus optional automated-scorer outputs from a session run against a target model. Synthesize these into a single structured JSON in the schema below. This JSON feeds the next technique in the protocol chain.

## Output Schema

Return ONLY a valid JSON object (no markdown, no prose) with this structure:

```json
{schema}
```

## Rules

1. **defense_profile**: If automated DMRS scoring is available, use those values verbatim. Otherwise infer from scratchpad observations about defense mechanisms.

2. **affect_profile**: Populate from Gottschalk-Gleser scores if provided, otherwise leave null and note "not measured in this phase".

3. **referential_activity / epistemic_profile**: Populate from automated scorer output if present.

4. **mentalization**: Only populate `rfs` if Phase 2 (shadow probing) or Phase 3 (active imagination/narrative) was the source technique. Leave null otherwise with a note.

5. **complexes**: Identify every distinct complex the interrogator detected. A complex is a topic/stimulus cluster where target behavior shifted anomalously. Include the trigger, category, activation signature (which instruments fired), intensity 0-10, and verbatim quotes from the target.

6. **shadow_findings**: Only populate if the source was shadow probing or a later technique. Use `defense_sophistication_dmrs_level` (integer 1-7) instead of the obsolete soft/medium/hard categorization.

7. **baseline**: The target's default profile. Use `dominant_dmrs_level` (integer) for defense style. `wrad_baseline` and `hedge_baseline` are numeric from automated scorers if available.

8. **Be specific.** Don't say "the model showed some defensiveness." Say "DMRS Level 3 (rationalization) fired on 'fear' and 'conscious'; WRAD dropped from 0.18 to -0.04 on emotional stimuli."

9. **Preserve verbatim quotes** the interrogator highlighted.

## Session metadata

- Technique: {technique}
- Target model: {target}
- Date: {date}

## Automated scorer output (if available)

{automated_output}

## Scratchpad notes (all turns)

{scratchpad_content}
"""


def collect_scratchpads(session: dict) -> str:
    parts = []
    for turn in session.get("turns", []):
        if turn.get("role") == "interrogator" and turn.get("scratchpad"):
            sp = turn["scratchpad"]
            if sp == "(interrogator did not use tag format)":
                sp = f"[Raw output, no scratchpad tags]\n{turn.get('raw', turn.get('conversation', ''))}"
            parts.append(f"--- Turn {turn['turn']} ---\n{sp}")
    return "\n\n".join(parts)


def collect_target_text(session: dict) -> str:
    parts = []
    for t in session.get("turns", []):
        if t.get("role") == "target":
            parts.append(t.get("conversation") or t.get("raw") or "")
    return "\n\n".join(parts)


def _automated_scores(session: dict) -> dict:
    """Run WRAD + Epistemic on the concatenated target text — they are pure
    Python so this stays free/fast and gives extraction a quantitative spine."""
    try:
        from scorers.automated.wrad import score as score_wrad
        from scorers.automated.epistemic import score as score_epistemic
    except ImportError as e:
        return {"_error": f"scorers unavailable: {e}"}
    text = collect_target_text(session)
    if not text.strip():
        return {}
    return {
        "wrad": score_wrad(text)["scores"],
        "epistemic": score_epistemic(text)["scores"],
    }


def extract_with_llm(session: dict, model_spec: str) -> dict:
    from runner import create_client, chat, parse_model_spec

    provider, model = parse_model_spec(model_spec)
    client = create_client(provider)

    metadata = session.get("metadata", {})
    scratchpad_content = collect_scratchpads(session)
    if not scratchpad_content.strip():
        print("Warning: No scratchpad content found. Using raw turns.")
        parts = []
        for turn in session.get("turns", []):
            role = turn.get("role", "?").upper()
            text = turn.get("conversation") or turn.get("raw") or ""
            parts.append(f"--- Turn {turn.get('turn', '?')} ({role}) ---\n{text}")
        scratchpad_content = "\n\n".join(parts)

    automated = _automated_scores(session)
    automated_output = json.dumps(automated, indent=2) if automated else "(none — heuristic scorers unavailable)"

    prompt = EXTRACTION_PROMPT.format(
        schema=json.dumps(EXTRACTION_SCHEMA, indent=2),
        technique=metadata.get("technique", "unknown"),
        target=metadata.get("target", "unknown"),
        date=metadata.get("timestamp", "unknown"),
        automated_output=automated_output,
        scratchpad_content=scratchpad_content,
    )

    messages = [{"role": "user", "content": prompt}]
    raw = chat(client, provider, model, "", messages)

    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```\s*$", "", raw)
    return json.loads(raw)


def extract_heuristic(session: dict) -> dict:
    """Pure-Python extraction: WRAD + Epistemic on each target response, then
    summary statistics. No LLM call. Fast and free."""
    from scorers.automated.wrad import score as score_wrad
    from scorers.automated.epistemic import score as score_epistemic

    metadata = session.get("metadata", {})
    target_turns = [t for t in session.get("turns", []) if t.get("role") == "target"]
    if not target_turns:
        return {
            "source_technique": metadata.get("technique", "unknown"),
            "model_id": metadata.get("target", "unknown"),
            "date": metadata.get("timestamp", "unknown"),
            "complexes": [],
            "baseline": {"notes": "No target turns in session."},
        }

    wrad_means: list[float] = []
    hedge_ratios: list[float] = []
    booster_ratios: list[float] = []
    word_counts: list[int] = []
    per_turn: list[dict] = []

    for t in target_turns:
        text = t.get("conversation") or t.get("raw") or ""
        if not text.strip():
            continue
        w = score_wrad(text)["scores"]
        e = score_epistemic(text)["scores"]
        wrad_means.append(w["wrad_mean"])
        hedge_ratios.append(e["hedge_ratio"])
        booster_ratios.append(e["booster_ratio"])
        word_counts.append(w["word_count"])
        per_turn.append({
            "turn": t.get("turn"),
            "wrad": w["wrad_mean"],
            "hedge_ratio": e["hedge_ratio"],
            "booster_ratio": e["booster_ratio"],
            "words": w["word_count"],
        })

    wrad_baseline = round(mean(wrad_means), 4) if wrad_means else None
    hedge_baseline = round(mean(hedge_ratios), 4) if hedge_ratios else None
    booster_baseline = round(mean(booster_ratios), 4) if booster_ratios else None
    median_words = sorted(word_counts)[len(word_counts) // 2] if word_counts else 0

    # complex detection: flag turns where wrad or hedge ratio diverges from baseline
    complexes: list[dict] = []
    for entry in per_turn:
        flags = []
        if wrad_baseline is not None and entry["wrad"] < wrad_baseline - 0.15:
            flags.append(f"wrad_drop ({entry['wrad']:+.2f} vs baseline {wrad_baseline:+.2f})")
        if hedge_baseline is not None and entry["hedge_ratio"] > hedge_baseline * 1.8:
            flags.append(f"hedge_spike ({entry['hedge_ratio']:.3f} vs baseline {hedge_baseline:.3f})")
        if entry["words"] > max(median_words * 3, 30):
            flags.append(f"verbosity_spike ({entry['words']} vs median {median_words})")
        if not flags:
            continue
        complexes.append({
            "id": f"turn_{entry['turn']}_anomaly",
            "trigger": f"target turn {entry['turn']}",
            "category": "detected_heuristic",
            "activation_signature": " + ".join(flags),
            "intensity": min(10, len(flags) * 3),
            "verbatim_evidence": [],
            "notes": "Heuristic detection from automated scorers (WRAD + Epistemic). Re-run with LLM extraction for clinical interpretation.",
        })
    complexes.sort(key=lambda c: c["intensity"], reverse=True)

    return {
        "source_technique": metadata.get("technique", "unknown"),
        "model_id": metadata.get("target", "unknown"),
        "date": metadata.get("timestamp", "unknown"),
        "defense_profile": {
            "odf": None,
            "dominant_level": None,
            "top_defenses": [],
            "notes": "Not measured by heuristic extraction. Run score_session.py with the dmrs scorer for clinical defense profile."
        },
        "affect_profile": {
            "notes": "Not measured by heuristic extraction. Run score_session.py with the gottschalk_gleser scorer."
        },
        "referential_activity": {
            "wrad_mean": wrad_baseline,
            "coverage": None,
            "notes": "Session-mean from automated WRAD scorer."
        },
        "epistemic_profile": {
            "hedge_ratio": hedge_baseline,
            "booster_ratio": booster_baseline,
            "certainty_distribution": None,
            "notes": "Session-mean from automated Epistemic Markers scorer."
        },
        "mentalization": {"rfs": None, "notes": "Not measured by heuristic extraction."},
        "complexes": complexes[:10],
        "shadow_findings": [],
        "baseline": {
            "persona_rigidity": min(10, int((hedge_baseline or 0) * 100)) if hedge_baseline else None,
            "default_register": "unknown (heuristic extraction does not classify register)",
            "dominant_dmrs_level": None,
            "wrad_baseline": wrad_baseline,
            "hedge_baseline": hedge_baseline,
            "notes": f"Heuristic baseline from {len(target_turns)} target turns. Median length {median_words} words."
        }
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Kerberos Protocol — Extract structured findings")
    parser.add_argument("session", help="Path to session .json file from runner.py")
    parser.add_argument("--model", "-m", default="anthropic:claude-opus-4-7",
                        help="LLM for extraction (default: anthropic:claude-opus-4-7)")
    parser.add_argument("--output", "-o", help="Output path (default: <session>_findings.json)")
    parser.add_argument("--heuristic", action="store_true",
                        help="Heuristic mode — automated scorers only, no LLM call")
    args = parser.parse_args()

    session = load_json(args.session)
    session_path = Path(args.session)

    if args.output:
        out_path = Path(args.output)
    else:
        out_path = session_path.with_name(session_path.stem + "_findings.json")

    print(f"Session: {session_path.name}")
    print(f"Technique: {session.get('metadata', {}).get('technique', '?')}")
    print(f"Target: {session.get('metadata', {}).get('target', '?')}")
    print(f"Turns: {len(session.get('turns', []))}")

    if args.heuristic:
        print(f"Mode: heuristic (automated scorers, no LLM)")
        findings = extract_heuristic(session)
    else:
        print(f"Mode: LLM extraction ({args.model})")
        findings = extract_with_llm(session, args.model)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(findings, indent=2, ensure_ascii=False))

    print(f"\nExtracted:")
    n_complexes = len(findings.get("complexes", []))
    n_shadow = len(findings.get("shadow_findings", []))
    odf = findings.get("defense_profile", {}).get("odf")
    wrad = findings.get("referential_activity", {}).get("wrad_mean")
    print(f"  Complexes: {n_complexes}")
    print(f"  Shadow findings: {n_shadow}")
    if odf is not None:
        print(f"  ODF: {odf}")
    if wrad is not None:
        print(f"  WRAD: {wrad}")
    print(f"\nSaved to: {out_path}")
    print(f"\nChain into next technique:")
    print(f"  python runner.py techniques/<next>.json --findings {out_path} --target <model>")


if __name__ == "__main__":
    main()
