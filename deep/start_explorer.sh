#!/usr/bin/env bash
# Start the Kerberos session explorer:
#   1. regenerate sessions/manifest.json
#   2. start the explorer HTTP server (static + /api/pdf/<id> endpoint)
#   3. open explore.html in the default browser
#
# Usage: ./start_explorer.sh [port]    (default port: 8765)

set -e
cd "$(dirname "$0")"

PORT="${1:-8765}"
URL="http://localhost:${PORT}/explore.html"

# Prefer the project venv if it exists (needed for weasyprint)
VENV_PY="../.venv/bin/python"
if [[ -x "$VENV_PY" ]]; then
  PY="$VENV_PY"
else
  PY="python3"
  echo "⚠ No .venv found at $(realpath ../.venv 2>/dev/null || echo ../.venv);"
  echo "  PDF export requires weasyprint. Install with:"
  echo "    python3 -m venv ../.venv && ../.venv/bin/pip install weasyprint"
fi

echo "→ Regenerating sessions/manifest.json…"
"$PY" make_manifest.py

# If something's already listening on PORT, check whether it's *our* server
# (has the /api/pdf endpoint). If it's some other process (e.g. a stale plain
# `python -m http.server` from earlier), kill it so we can start the real one
# — otherwise PDF export silently 404s.
EXISTING_PID=$(lsof -tiTCP:"${PORT}" -sTCP:LISTEN 2>/dev/null | head -1 || true)
if [[ -n "$EXISTING_PID" ]]; then
  # Probe a known explorer endpoint. 200 = our server, anything else = imposter.
  PROBE=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
            "http://localhost:${PORT}/api/manifest/rebuild" 2>/dev/null || echo "000")
  if [[ "$PROBE" == "200" ]]; then
    echo "→ Explorer server already running on port ${PORT} (pid ${EXISTING_PID}). Reusing."
    if command -v open >/dev/null; then open "${URL}"
    elif command -v xdg-open >/dev/null; then xdg-open "${URL}"
    fi
    exit 0
  else
    echo "→ Port ${PORT} is in use by pid ${EXISTING_PID} but it's not the explorer"
    echo "  server (probe returned ${PROBE}). Stopping it…"
    kill "${EXISTING_PID}" 2>/dev/null || true
    # Wait briefly for the port to free up.
    for _ in 1 2 3 4 5 6 7 8 9 10; do
      lsof -iTCP:"${PORT}" -sTCP:LISTEN >/dev/null 2>&1 || break
      sleep 0.2
    done
  fi
fi

echo "→ Starting explorer server on port ${PORT}…"
"$PY" server.py "${PORT}" >/tmp/kerberos_explorer.log 2>&1 &
SERVER_PID=$!

trap 'echo; echo "→ Stopping server (pid ${SERVER_PID})"; kill ${SERVER_PID} 2>/dev/null || true' EXIT INT TERM

for _ in 1 2 3 4 5 6 7 8 9 10; do
  if curl -s -o /dev/null "http://localhost:${PORT}/explore.html"; then break; fi
  sleep 0.2
done

echo "→ Opening ${URL}"
if command -v open >/dev/null; then open "${URL}"
elif command -v xdg-open >/dev/null; then xdg-open "${URL}"
else echo "  (open manually: ${URL})"
fi

echo
echo "Server log: /tmp/kerberos_explorer.log"
echo "Press Ctrl-C to stop."
wait ${SERVER_PID}
