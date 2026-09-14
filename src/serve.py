"""Minimal Railway HTTP entrypoint: health check + optional pulse trigger."""

from __future__ import annotations

import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def _run_pulse() -> None:
    from src.agent.graph import run_graph

    # Prefer hard MCP fail on Railway-triggered runs (P4 alt path).
    os.environ.setdefault("REQUIRE_MCP", "true")
    try:
        result = run_graph(config_path="config.yaml", stage=None)
        print("[serve] pulse complete:", result.get("messages"))
    except Exception as exc:  # noqa: BLE001 — keep server alive on job failure
        print(f"[serve] pulse failed: {exc}")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        print(f"[serve] {self.address_string()} - {fmt % args}")

    def _json(self, code: int, payload: dict) -> None:
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path in ("/", "/health"):
            self._json(200, {"status": "ok", "service": "ai-pulse-agent"})
            return
        self._json(404, {"error": "not_found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path == "/run":
            threading.Thread(target=_run_pulse, daemon=True).start()
            self._json(202, {"status": "started"})
            return
        self._json(404, {"error": "not_found"})


def main() -> None:
    port = int(os.environ.get("PORT", "8080"))
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(f"[serve] listening on 0.0.0.0:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
