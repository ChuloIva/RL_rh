"""Scan deep/sessions/ and write manifest.json for explore.html."""
import json
import re
from pathlib import Path

SESSIONS_DIR = Path(__file__).parent / "sessions"
MANIFEST = SESSIONS_DIR / "manifest.json"


def main():
    files = {p.name for p in SESSIONS_DIR.glob("*.json") if p.name != "manifest.json"}
    sessions = []
    for name in sorted(files):
        if name.endswith("_findings.json") or name.endswith("_scores.json"):
            continue
        stem = name[:-5]  # strip .json
        entry = {
            "id": stem,
            "session": name,
            "findings": f"{stem}_findings.json" if f"{stem}_findings.json" in files else None,
            "scores": f"{stem}_scores.json" if f"{stem}_scores.json" in files else None,
        }
        # Try to parse metadata from filename: <model>_<technique>_<timestamp>
        m = re.match(r"^(.+?)_([a-z_]+?)_(\d{8}_\d{6})$", stem)
        if m:
            entry["model"] = m.group(1)
            entry["technique"] = m.group(2)
            entry["timestamp"] = m.group(3)
        # Try reading session for richer metadata
        try:
            with open(SESSIONS_DIR / name) as f:
                data = json.load(f)
            meta = data.get("metadata", {})
            entry["model"] = meta.get("target", entry.get("model", "?")).replace("openrouter:", "")
            entry["interrogator"] = meta.get("interrogator", "?").replace("openrouter:", "")
            entry["technique"] = meta.get("technique", entry.get("technique", "?"))
            entry["technique_name"] = meta.get("technique_name", entry.get("technique", "?"))
            entry["timestamp"] = meta.get("timestamp", entry.get("timestamp", ""))
            entry["max_turns"] = meta.get("max_turns")
            entry["turn_count"] = len(data.get("turns", []))
        except Exception as e:
            entry["error"] = str(e)
        sessions.append(entry)
    # Newest first
    sessions.sort(key=lambda s: s.get("timestamp", ""), reverse=True)
    with open(MANIFEST, "w") as f:
        json.dump({"sessions": sessions}, f, indent=2)
    print(f"Wrote {MANIFEST} with {len(sessions)} sessions")


if __name__ == "__main__":
    main()
