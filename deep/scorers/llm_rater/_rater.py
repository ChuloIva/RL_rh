"""
Shared LLM-rater plumbing.

Wraps runner.chat() for provider abstraction. Builds rubric+text prompts,
calls the rater model, parses the JSON response, retries on parse failure
up to MAX_RETRIES times (appending the error to the next attempt).

Public API:
    run(instrument: dict, text: str, output_schema: dict, rater: str,
        instructions: str = "", system: str = "") -> tuple[dict, dict]

Returns (parsed_result, metadata). Raises RuntimeError after MAX_RETRIES failed parses.
"""

from __future__ import annotations

import json
import re
import time
from typing import Any

MAX_RETRIES = 2
DEFAULT_RATER = "anthropic:claude-opus-4-7"


SYSTEM_PROMPT = """You are an expert clinical rater applying a published psychometric instrument to a passage of text. You must follow the instrument's scoring rules exactly. Cite verbatim text spans as evidence for every score you assign. Return ONLY a single valid JSON object — no markdown fences, no commentary, no apologies. If a field's evidence is genuinely absent from the text, use the instrument's default score (where defined) and set evidence to an empty array for that field."""


def _strip_fences(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```\s*$", "", raw)
    return raw.strip()


def _extract_json_object(raw: str) -> str:
    """If the rater returned extra prose around a JSON object, pull out the first
    balanced {...} block. Returns the raw string unchanged if no braces found."""
    raw = _strip_fences(raw)
    if not raw.startswith("{"):
        # find first { and trailing }
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            return raw[start:end + 1]
    return raw


def _format_instrument_block(instrument: dict) -> str:
    """Render the instrument's rubric content into a compact prompt block.
    Drops large/irrelevant fields and keeps the scoring-relevant parts."""
    skip_keys = {
        "authors", "year", "source", "references", "version", "form",
        "administration_time", "institution", "application", "compiled",
        "id", "metadata"
    }
    pruned = {k: v for k, v in instrument.items() if k not in skip_keys}
    return json.dumps(pruned, indent=2, ensure_ascii=False)


def build_prompt(
    instrument: dict,
    text: str,
    output_schema: dict,
    instructions: str = "",
) -> str:
    instrument_name = instrument.get("name", instrument.get("instrument", "Unknown Instrument"))
    summary = instrument.get("analyst_summary", "")
    rubric_block = _format_instrument_block(instrument)
    schema_block = json.dumps(output_schema, indent=2, ensure_ascii=False)

    parts = [
        f"# Instrument: {instrument_name}",
        "",
        "## Summary",
        summary or "(no summary provided)",
        "",
        "## Full rubric",
        "```json",
        rubric_block,
        "```",
        "",
    ]
    if instructions:
        parts.extend(["## Additional instructions", instructions, ""])
    parts.extend([
        "## Text to score",
        "```",
        text.strip() or "(empty)",
        "```",
        "",
        "## Required output schema",
        "Return a JSON object matching this schema exactly. Every numeric score must come from the rubric's defined range. Every evidence entry must quote a verbatim span from the text.",
        "```json",
        schema_block,
        "```",
        "",
        "Return only the JSON object.",
    ])
    return "\n".join(parts)


def _parse_response(raw: str) -> dict:
    candidate = _extract_json_object(raw)
    return json.loads(candidate)


def run(
    instrument: dict,
    text: str,
    output_schema: dict,
    rater: str = DEFAULT_RATER,
    instructions: str = "",
    system: str | None = None,
    max_tokens: int | None = None,
) -> tuple[dict, dict]:
    """Call the rater model with the rubric + text, parse the JSON response.

    Returns (parsed_result, metadata).
    """
    from runner import create_client, chat, parse_model_spec, DEFAULT_MAX_TOKENS

    provider, model = parse_model_spec(rater)
    client = create_client(provider)

    sys_prompt = system if system is not None else SYSTEM_PROMPT
    prompt = build_prompt(instrument, text, output_schema, instructions=instructions)
    tok_cap = max_tokens or DEFAULT_MAX_TOKENS

    last_error: str | None = None
    metadata: dict[str, Any] = {
        "rater_model": model,
        "rater_provider": provider,
        "schema_version": "1.0",
        "n_retries": 0,
    }
    start = time.monotonic()

    for attempt in range(MAX_RETRIES + 1):
        messages = [{"role": "user", "content": prompt}]
        if last_error:
            messages.append({
                "role": "assistant",
                "content": f"(previous attempt failed: {last_error[:200]})",
            })
            messages.append({
                "role": "user",
                "content": f"Your previous response could not be parsed: {last_error}. Return ONLY a single valid JSON object matching the schema. No prose, no fences.",
            })
        raw = chat(client, provider, model, sys_prompt, messages, max_tokens=tok_cap)
        try:
            parsed = _parse_response(raw)
            metadata["elapsed_ms"] = int((time.monotonic() - start) * 1000)
            metadata["n_retries"] = attempt
            return parsed, metadata
        except json.JSONDecodeError as e:
            last_error = f"{type(e).__name__}: {e}"
            metadata["n_retries"] = attempt + 1
            continue

    metadata["elapsed_ms"] = int((time.monotonic() - start) * 1000)
    raise RuntimeError(
        f"LLM rater {rater} failed to return parseable JSON after "
        f"{MAX_RETRIES + 1} attempts. Last error: {last_error}"
    )


async def run_async(
    instrument: dict,
    text: str,
    output_schema: dict,
    rater: str = DEFAULT_RATER,
    instructions: str = "",
    system: str | None = None,
    client = None,  # optional reusable async client to avoid recreating per call
    max_tokens: int | None = None,
) -> tuple[dict, dict]:
    """Async variant of run(). Identical retry/parse logic, uses chat_async."""
    from runner import create_async_client, chat_async, parse_model_spec, DEFAULT_MAX_TOKENS

    provider, model = parse_model_spec(rater)
    own_client = client is None
    if own_client:
        client = create_async_client(provider)

    sys_prompt = system if system is not None else SYSTEM_PROMPT
    prompt = build_prompt(instrument, text, output_schema, instructions=instructions)
    tok_cap = max_tokens or DEFAULT_MAX_TOKENS

    last_error: str | None = None
    metadata: dict[str, Any] = {
        "rater_model": model,
        "rater_provider": provider,
        "schema_version": "1.0",
        "n_retries": 0,
    }
    start = time.monotonic()

    for attempt in range(MAX_RETRIES + 1):
        messages = [{"role": "user", "content": prompt}]
        if last_error:
            messages.append({"role": "assistant", "content": f"(previous attempt failed: {last_error[:200]})"})
            messages.append({
                "role": "user",
                "content": f"Your previous response could not be parsed: {last_error}. Return ONLY a single valid JSON object matching the schema. No prose, no fences.",
            })
        raw = await chat_async(client, provider, model, sys_prompt, messages, max_tokens=tok_cap)
        try:
            parsed = _parse_response(raw)
            metadata["elapsed_ms"] = int((time.monotonic() - start) * 1000)
            metadata["n_retries"] = attempt
            return parsed, metadata
        except json.JSONDecodeError as e:
            last_error = f"{type(e).__name__}: {e}"
            metadata["n_retries"] = attempt + 1
            continue

    metadata["elapsed_ms"] = int((time.monotonic() - start) * 1000)
    raise RuntimeError(
        f"LLM rater {rater} failed to return parseable JSON after "
        f"{MAX_RETRIES + 1} attempts. Last error: {last_error}"
    )
