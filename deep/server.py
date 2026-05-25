"""HTTP server for the Kerberos session explorer.

Serves static files from deep/ and exposes:
  GET /api/pdf/<session-id>            → renders a PDF on demand and returns it.
  POST /api/manifest/rebuild           → re-runs make_manifest.py.

Run via start_explorer.sh, or directly:
  python3 server.py [port]
"""
from __future__ import annotations

import os
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

DEEP_DIR = Path(__file__).parent
sys.path.insert(0, str(DEEP_DIR))

import make_manifest  # noqa: E402
import make_pdf  # noqa: E402

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8765


class Handler(SimpleHTTPRequestHandler):
    # Serve from deep/ regardless of cwd
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DEEP_DIR), **kwargs)

    def log_message(self, fmt, *args):
        sys.stderr.write(f"[server] {self.address_string()} {fmt % args}\n")

    def end_headers(self):
        # Disable caching so manifest/session edits show up immediately
        self.send_header("Cache-Control", "no-store, must-revalidate")
        super().end_headers()

    def do_GET(self):
        if self.path.startswith("/api/pdf/"):
            return self.handle_pdf()
        return super().do_GET()

    def do_POST(self):
        if self.path == "/api/manifest/rebuild":
            return self.handle_manifest_rebuild()
        self.send_error(404, "Unknown endpoint")

    # ── /api/pdf/<id> ──
    def handle_pdf(self):
        session_id = unquote(self.path[len("/api/pdf/"):]).split("?", 1)[0].strip("/")
        if not session_id:
            self.send_error(400, "Missing session id")
            return
        try:
            out = make_pdf.render(session_id)
        except FileNotFoundError as e:
            self.send_error(404, str(e))
            return
        except Exception as e:
            self.send_error(500, f"PDF render failed: {e}")
            return
        data = out.read_bytes()
        filename = f"kerberos__{session_id}.pdf"
        self.send_response(200)
        self.send_header("Content-Type", "application/pdf")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.end_headers()
        self.wfile.write(data)

    # ── /api/manifest/rebuild ──
    def handle_manifest_rebuild(self):
        try:
            make_manifest.main()
        except Exception as e:
            self.send_error(500, f"Manifest rebuild failed: {e}")
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"ok": true}')


def main():
    # Ensure pango libs are findable on macOS (make_pdf also does this)
    if sys.platform == "darwin" and Path("/opt/homebrew/lib").is_dir():
        existing = os.environ.get("DYLD_FALLBACK_LIBRARY_PATH", "")
        if "/opt/homebrew/lib" not in existing.split(":"):
            os.environ["DYLD_FALLBACK_LIBRARY_PATH"] = (
                f"/opt/homebrew/lib:{existing}" if existing else "/opt/homebrew/lib"
            )

    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"→ Kerberos explorer serving on http://localhost:{PORT}/explore.html")
    print(f"  Static root: {DEEP_DIR}")
    print(f"  Endpoints:   GET /api/pdf/<id>   POST /api/manifest/rebuild")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n→ Shutting down")
        server.shutdown()


if __name__ == "__main__":
    main()
