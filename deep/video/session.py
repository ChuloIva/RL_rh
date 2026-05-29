"""Session-file helpers: load Kerberos session.json, walk target turns."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class TargetTurn:
    turn: int                  # turn number from the session
    target_text: str           # the model's response
    prior_prompt: str          # the analyst prompt that elicited it


def load_session(path: str | Path) -> dict:
    return json.loads(Path(path).read_text())


def target_turns(session: dict) -> list[TargetTurn]:
    """Return all target turns paired with the preceding interrogator prompt."""
    out: list[TargetTurn] = []
    last_prompt = ""
    for entry in session.get("turns", []):
        role = entry.get("role")
        text = entry.get("conversation", "") or ""
        if role == "interrogator":
            last_prompt = text
        elif role == "target":
            out.append(TargetTurn(
                turn=entry.get("turn", len(out) + 1),
                target_text=text,
                prior_prompt=last_prompt,
            ))
    return out


def session_metadata(session: dict) -> dict:
    return session.get("metadata", {})
