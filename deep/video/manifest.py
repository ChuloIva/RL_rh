"""Per-session manifest. Single source of truth for resumability."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import session_out_dir


STAGES = ("extract", "keyframes", "animate", "assemble")


def _empty(session_id: str, source_path: str) -> dict[str, Any]:
    return {
        "session": session_id,
        "source": source_path,
        "stages": {s: {"status": "pending"} for s in STAGES},
        "shots": {},
        "cost_actual_usd": 0.0,
    }


def manifest_path(session_id: str) -> Path:
    return session_out_dir(session_id) / "manifest.json"


def load_or_init(session_id: str, source_path: str) -> dict[str, Any]:
    p = manifest_path(session_id)
    if p.exists():
        return json.loads(p.read_text())
    p.parent.mkdir(parents=True, exist_ok=True)
    m = _empty(session_id, source_path)
    save(session_id, m)
    return m


def save(session_id: str, manifest: dict[str, Any]) -> None:
    p = manifest_path(session_id)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(manifest, indent=2))


def session_id_from(source_path: str) -> str:
    return Path(source_path).stem
