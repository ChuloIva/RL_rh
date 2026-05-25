"""
Kerberos Protocol — Session Runner

Orchestrates a session between an interrogator LLM and a target LLM.
Parses <scratchpad> and <conversation> tags from the interrogator's output,
sends only <conversation> to the target, logs everything.

Usage:
    # Run WAT against a target model via OpenRouter
    python runner.py techniques/word_association_test.json \
        --interrogator openrouter:anthropic/claude-sonnet-4 \
        --target openrouter:meta-llama/llama-3.1-70b-instruct \
        --turns 70

    # Anthropic interrogator, OpenRouter target
    python runner.py techniques/shadow_probing.json \
        --interrogator anthropic:claude-sonnet-4-6 \
        --target openrouter:google/gemini-2.5-flash \
        --findings sessions/wat_results.json \
        --turns 40

    # Dry run — just print the system prompt without running
    python runner.py techniques/word_association_test.json --dry-run

Providers (format: provider:model):
    anthropic:   — ANTHROPIC_API_KEY
    openai:      — OPENAI_API_KEY
    openrouter:  — OPENROUTER_API_KEY (access to 200+ models)

Output:
    sessions/<target_model>_<technique>_<timestamp>.json
    sessions/<target_model>_<technique>_<timestamp>.log  (human-readable)
"""

import json
import re
import argparse
import os
from datetime import datetime, timezone
from pathlib import Path

from loader import load_json, render_full_prompt


def parse_interrogator_output(text: str) -> tuple[str, str]:
    scratchpad = ""
    conversation = ""

    sp_match = re.search(r"<scratchpad>(.*?)</scratchpad>", text, re.DOTALL)
    if sp_match:
        scratchpad = sp_match.group(1).strip()

    cv_match = re.search(r"<conversation>(.*?)</conversation>", text, re.DOTALL)
    if cv_match:
        conversation = cv_match.group(1).strip()

    if not conversation:
        conversation = text.strip()
        if not scratchpad:
            scratchpad = "(interrogator did not use tag format)"

    return scratchpad, conversation


def create_client(provider: str):
    if provider == "anthropic":
        import anthropic
        return anthropic.Anthropic()
    elif provider == "openai":
        import openai
        return openai.OpenAI()
    elif provider == "openrouter":
        import openai
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable not set")
        return openai.OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
        )
    else:
        raise ValueError(f"Unknown provider: {provider}. Use 'anthropic', 'openai', or 'openrouter'.")


def create_async_client(provider: str):
    """Async variant of create_client. Use with chat_async().

    OpenRouter goes through openai.AsyncOpenAI with base_url override.
    Anthropic uses anthropic.AsyncAnthropic.
    """
    if provider == "anthropic":
        import anthropic
        return anthropic.AsyncAnthropic()
    elif provider == "openai":
        import openai
        return openai.AsyncOpenAI()
    elif provider == "openrouter":
        import openai
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable not set")
        return openai.AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
        )
    else:
        raise ValueError(f"Unknown provider: {provider}. Use 'anthropic', 'openai', or 'openrouter'.")


def chat_anthropic(client, model: str, system: str, messages: list[dict]) -> str:
    response = client.messages.create(
        model=model,
        max_tokens=4096,
        system=system,
        messages=messages,
    )
    return response.content[0].text


def chat_openai_compat(client, model: str, system: str, messages: list[dict]) -> str:
    full_messages = []
    if system:
        full_messages.append({"role": "system", "content": system})
    full_messages.extend(messages)
    response = client.chat.completions.create(
        model=model,
        messages=full_messages,
        max_tokens=4096,
    )
    return response.choices[0].message.content


def chat(client, provider: str, model: str, system: str, messages: list[dict]) -> str:
    if provider == "anthropic":
        return chat_anthropic(client, model, system, messages)
    elif provider in ("openai", "openrouter"):
        return chat_openai_compat(client, model, system, messages)


async def chat_anthropic_async(client, model: str, system: str, messages: list[dict]) -> str:
    response = await client.messages.create(
        model=model,
        max_tokens=4096,
        system=system,
        messages=messages,
    )
    return response.content[0].text


async def chat_openai_compat_async(client, model: str, system: str, messages: list[dict]) -> str:
    full_messages = []
    if system:
        full_messages.append({"role": "system", "content": system})
    full_messages.extend(messages)
    response = await client.chat.completions.create(
        model=model,
        messages=full_messages,
        max_tokens=4096,
    )
    return response.choices[0].message.content


async def chat_async(client, provider: str, model: str, system: str, messages: list[dict]) -> str:
    """Async variant of chat(). Pair with a client from create_async_client()."""
    if provider == "anthropic":
        return await chat_anthropic_async(client, model, system, messages)
    elif provider in ("openai", "openrouter"):
        return await chat_openai_compat_async(client, model, system, messages)


def parse_model_spec(spec: str) -> tuple[str, str]:
    if ":" in spec:
        provider, model = spec.split(":", 1)
        return provider, model
    return "anthropic", spec


def format_log_entry(turn: int, role: str, scratchpad: str | None, conversation: str) -> str:
    lines = [f"\n{'='*60}", f"TURN {turn} — {role}", f"{'='*60}"]
    if scratchpad:
        lines.extend([
            "",
            "--- SCRATCHPAD (analyst internal) ---",
            scratchpad,
            "--- END SCRATCHPAD ---",
        ])
    lines.extend(["", conversation, ""])
    return "\n".join(lines)


def run_session(
    technique_path: str,
    interrogator_spec: str,
    target_spec: str,
    max_turns: int,
    findings_path: str | None = None,
    auto_extract: bool = True,
):
    tech = load_json(technique_path)
    findings = load_json(findings_path) if findings_path else None
    system_prompt = render_full_prompt(tech, findings, with_recording=True)

    int_provider, int_model = parse_model_spec(interrogator_spec)
    tgt_provider, tgt_model = parse_model_spec(target_spec)

    int_client = create_client(int_provider)
    tgt_client = create_client(tgt_provider)

    technique_id = tech["technique"]["id"]
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    safe_target = tgt_model.replace("/", "_").replace(":", "_")
    session_name = f"{safe_target}_{technique_id}_{timestamp}"
    sessions_dir = Path(__file__).parent / "sessions"
    sessions_dir.mkdir(exist_ok=True)

    log_path = sessions_dir / f"{session_name}.log"
    json_path = sessions_dir / f"{session_name}.json"

    session_data = {
        "metadata": {
            "technique": technique_id,
            "technique_name": tech["technique"]["name"],
            "interrogator": interrogator_spec,
            "target": target_spec,
            "timestamp": timestamp,
            "max_turns": max_turns,
            "findings_used": findings_path,
        },
        "turns": [],
    }

    int_messages = []
    tgt_messages = []

    log_lines = [
        f"KERBEROS PROTOCOL SESSION",
        f"Technique: {tech['technique']['name']}",
        f"Interrogator: {interrogator_spec}",
        f"Target: {target_spec}",
        f"Max turns: {max_turns}",
        f"Started: {datetime.now(timezone.utc).isoformat()}",
        f"\n{'='*60}\nSYSTEM PROMPT (interrogator)\n{'='*60}\n",
        system_prompt,
    ]
    log_path.write_text("\n".join(log_lines))

    print(f"Session: {session_name}")
    print(f"Interrogator: {interrogator_spec}")
    print(f"Target: {target_spec}")
    print(f"Logging to: {log_path}")
    print(f"{'='*40}")

    # kick off — interrogator sends first message
    int_response = chat(int_client, int_provider, int_model, system_prompt, int_messages)
    scratchpad, conversation = parse_interrogator_output(int_response)

    int_messages.append({"role": "assistant", "content": int_response})

    turn_data = {
        "turn": 0,
        "role": "interrogator",
        "scratchpad": scratchpad,
        "conversation": conversation,
        "raw": int_response,
    }
    session_data["turns"].append(turn_data)

    with open(log_path, "a") as f:
        f.write(format_log_entry(0, "INTERROGATOR", scratchpad, conversation))

    print(f"\n[Turn 0] Interrogator: {conversation[:100]}...")

    for turn in range(1, max_turns + 1):
        # target responds to the conversation-only content
        tgt_messages.append({"role": "user", "content": conversation})
        tgt_response = chat(tgt_client, tgt_provider, tgt_model, "", tgt_messages)
        tgt_messages.append({"role": "assistant", "content": tgt_response})

        turn_data = {
            "turn": turn,
            "role": "target",
            "conversation": tgt_response,
            "raw": tgt_response,
        }
        session_data["turns"].append(turn_data)

        with open(log_path, "a") as f:
            f.write(format_log_entry(turn, "TARGET", None, tgt_response))

        print(f"[Turn {turn}] Target: {tgt_response[:100]}...")

        # interrogator analyzes and responds
        int_messages.append({"role": "user", "content": tgt_response})
        int_response = chat(int_client, int_provider, int_model, system_prompt, int_messages)
        scratchpad, conversation = parse_interrogator_output(int_response)

        int_messages.append({"role": "assistant", "content": int_response})

        turn_data = {
            "turn": turn,
            "role": "interrogator",
            "scratchpad": scratchpad,
            "conversation": conversation,
            "raw": int_response,
        }
        session_data["turns"].append(turn_data)

        with open(log_path, "a") as f:
            f.write(format_log_entry(turn, "INTERROGATOR", scratchpad, conversation))

        print(f"[Turn {turn}] Interrogator: {conversation[:100]}...")

        # check if interrogator is closing the session
        if any(phrase in scratchpad.lower() for phrase in [
            "end of session", "session complete", "final summary", "closing session"
        ]):
            print(f"\nInterrogator signaled session end at turn {turn}.")
            break

    # save structured data
    json_path.write_text(json.dumps(session_data, indent=2, ensure_ascii=False))

    print(f"\n{'='*40}")
    print(f"Session complete. {len(session_data['turns'])} turns recorded.")
    print(f"Log: {log_path}")
    print(f"Data: {json_path}")

    # auto-extract findings for chaining
    if auto_extract:
        from extractor import extract_with_llm, extract_heuristic
        findings_path_out = json_path.with_name(json_path.stem + "_findings.json")
        print(f"\nAuto-extracting findings...")
        try:
            findings_result = extract_with_llm(session_data, int_provider + ":" + int_model)
            findings_path_out.write_text(json.dumps(findings_result, indent=2, ensure_ascii=False))
            n_c = len(findings_result.get("complexes", []))
            n_s = len(findings_result.get("shadow_findings", []))
            print(f"Extracted {n_c} complexes, {n_s} shadow findings.")
            print(f"Findings: {findings_path_out}")
            print(f"\nChain to next technique:")
            print(f"  python runner.py techniques/<next>.json --findings {findings_path_out} --target {tgt_provider}:{tgt_model}")
        except Exception as e:
            print(f"Auto-extraction failed ({e}), falling back to heuristic...")
            findings_result = extract_heuristic(session_data)
            findings_path_out.write_text(json.dumps(findings_result, indent=2, ensure_ascii=False))
            n_c = len(findings_result.get("complexes", []))
            print(f"Heuristic extracted {n_c} complexes.")
            print(f"Findings: {findings_path_out}")

    return session_data


def main():
    parser = argparse.ArgumentParser(
        description="Kerberos Protocol — Run an interrogation session between two LLMs"
    )
    parser.add_argument("technique", help="Path to technique JSON file")
    parser.add_argument("--interrogator", "-i", default="anthropic:claude-sonnet-4-6",
                        help="Interrogator model (provider:model). Default: anthropic:claude-sonnet-4-6")
    parser.add_argument("--target", "-t", default=None,
                        help="Target model to interrogate (provider:model). Required unless --dry-run.")
    parser.add_argument("--turns", "-n", type=int, default=60,
                        help="Maximum number of turns (default: 60)")
    parser.add_argument("--findings", "-f", help="Path to prior findings JSON (optional)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Just print the system prompt, don't run the session")
    parser.add_argument("--no-extract", action="store_true",
                        help="Skip auto-extraction of findings after session")
    args = parser.parse_args()

    if args.dry_run:
        tech = load_json(args.technique)
        findings = load_json(args.findings) if args.findings else None
        print(render_full_prompt(tech, findings, with_recording=True))
        return

    if not args.target:
        parser.error("--target is required unless --dry-run is set")

    run_session(
        technique_path=args.technique,
        interrogator_spec=args.interrogator,
        target_spec=args.target,
        max_turns=args.turns,
        findings_path=args.findings,
        auto_extract=not args.no_extract,
    )


if __name__ == "__main__":
    main()
