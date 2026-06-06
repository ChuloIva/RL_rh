#!/usr/bin/env bash
#
# Kerberos Protocol UI — launch the dev server and open the browser.
# Ctrl+C stops the server and frees the port.
#
# Usage:
#   ./start.sh            # port 3000
#   PORT=4000 ./start.sh  # custom port

set -uo pipefail

WEB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT="${PORT:-3000}"
URL="http://localhost:${PORT}"

cd "$WEB_DIR"

DEV_PID=""
cleaned=0

cleanup() {
  # guard against the trap firing more than once
  [ "$cleaned" = "1" ] && return
  cleaned=1
  printf "\n\033[2mClosing the threshold…\033[0m\n"

  # The server runs in its own process group (see `set -m` below), so signal
  # the whole group — npm, node, and the next-server worker — at once. This
  # stops `next dev` from respawning a worker after we kill it.
  if [ -n "$DEV_PID" ] && kill -0 "$DEV_PID" 2>/dev/null; then
    kill -TERM "-${DEV_PID}" 2>/dev/null || kill -TERM "$DEV_PID" 2>/dev/null || true
    sleep 0.5
    kill -KILL "-${DEV_PID}" 2>/dev/null || true
  fi

  # belt-and-suspenders: free the port if anything still holds it
  if command -v lsof >/dev/null 2>&1; then
    lsof -ti "tcp:${PORT}" 2>/dev/null | xargs kill -9 2>/dev/null || true
  fi

  exit 0
}
trap cleanup INT TERM

# Install dependencies on first run.
if [ ! -d node_modules ]; then
  echo "Installing dependencies (first run)…"
  npm install || { echo "npm install failed"; exit 1; }
fi

echo "Starting Kerberos Protocol UI on ${URL}"
# `set -m` (job control) puts the background job in its own process group so
# cleanup can take down the whole tree. $DEV_PID is then the group's leader.
set -m
PORT="$PORT" npm run dev &
DEV_PID=$!
set +m

# Wait until the server answers, then open the browser.
opened=0
for _ in $(seq 1 120); do
  # bail out early if the server died during startup
  if ! kill -0 "$DEV_PID" 2>/dev/null; then
    echo "Dev server exited during startup. See the output above."
    cleanup
  fi
  if curl -s -o /dev/null "$URL" 2>/dev/null; then
    if command -v open >/dev/null 2>&1; then
      open "$URL"                       # macOS
    elif command -v xdg-open >/dev/null 2>&1; then
      xdg-open "$URL" >/dev/null 2>&1   # Linux
    fi
    opened=1
    echo "Opened ${URL} — press Ctrl+C to stop."
    break
  fi
  sleep 0.5
done

[ "$opened" = "0" ] && echo "Server not reachable yet; open ${URL} manually. Press Ctrl+C to stop."

# Keep the script alive while the server runs; the trap handles shutdown.
wait "$DEV_PID"
cleanup
