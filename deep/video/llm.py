"""Thin OpenRouter wrapper. Mirrors the provider:model spec used in runner.py."""

from __future__ import annotations

import json
import os
import re
import time


def parse_model_spec(spec: str) -> tuple[str, str]:
    if ":" in spec:
        provider, model = spec.split(":", 1)
        return provider, model
    return "openrouter", spec


def _client(provider: str, timeout: float = 120.0):
    if provider == "openrouter":
        import openai
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            raise RuntimeError("OPENROUTER_API_KEY not set")
        return openai.OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
            timeout=timeout,
            max_retries=0,
        )
    if provider == "anthropic":
        import anthropic
        return anthropic.Anthropic()
    if provider == "openai":
        import openai
        return openai.OpenAI()
    raise ValueError(f"unknown provider: {provider}")


def chat(spec: str, system: str, user: str, max_tokens: int = 4096,
         timeout: float = 120.0, attempts: int = 3) -> str:
    provider, model = parse_model_spec(spec)

    last: Exception | None = None
    for i in range(attempts):
        client = _client(provider, timeout=timeout)
        try:
            if provider == "anthropic":
                resp = client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    system=system,
                    messages=[{"role": "user", "content": user}],
                )
                return resp.content[0].text

            msgs = []
            if system:
                msgs.append({"role": "system", "content": system})
            msgs.append({"role": "user", "content": user})
            resp = client.chat.completions.create(
                model=model,
                messages=msgs,
                max_tokens=max_tokens,
            )
            return resp.choices[0].message.content
        except Exception as e:  # noqa: BLE001
            last = e
            if i == attempts - 1:
                break
            sleep_s = 5.0 * (i + 1)
            print(f"[llm] attempt {i+1} failed: {type(e).__name__}: {e}; retry in {sleep_s}s")
            time.sleep(sleep_s)
    raise RuntimeError(f"llm.chat failed after {attempts} attempts: {last}") from last


_JSON_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


def chat_json(spec: str, system: str, user: str, max_tokens: int = 4096,
              timeout: float = 120.0, attempts: int = 3) -> dict:
    """Like chat() but extracts a JSON object from the response.

    Tolerates fenced code blocks and stray prose around the JSON.
    """
    raw = chat(spec, system, user, max_tokens=max_tokens,
               timeout=timeout, attempts=attempts)
    text = raw.strip()

    m = _JSON_FENCE.search(text)
    if m:
        text = m.group(1).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start : end + 1])
        raise
