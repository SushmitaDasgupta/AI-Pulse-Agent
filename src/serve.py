"""Railway HTTP entrypoint: health, full pulse run, Doc append + Gmail draft."""

from __future__ import annotations

import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse


DEFAULT_CORS_ORIGINS = (
    "https://ai-pulse-agent-beta.vercel.app,"
    "http://localhost:5173,"
    "http://127.0.0.1:5173"
)


def _cors_origins() -> list[str]:
    raw = os.environ.get("CORS_ORIGINS", DEFAULT_CORS_ORIGINS)
    return [part.strip() for part in raw.split(",") if part.strip()]


def _run_pulse() -> None:
    from src.agent.graph import run_graph

    # Prefer hard MCP fail on Railway-triggered runs (P4 alt path).
    os.environ.setdefault("REQUIRE_MCP", "true")
    try:
        result = run_graph(config_path="config.yaml", stage=None)
        print("[serve] pulse complete:", result.get("messages"))
    except Exception as exc:  # noqa: BLE001 — keep server alive on job failure
        print(f"[serve] pulse failed: {exc}")


def _deliver_pulse(payload: dict[str, Any]) -> dict[str, Any]:
    """Append Doc + create Gmail draft via MCP (sync; used by the web UI)."""
    from pathlib import Path

    from src.agent.schemas import PulseResult
    from src.agent.tools.delivery import draft_email_via_mcp, publish_docs_via_mcp
    from src.config import load_config

    cfg = load_config("config.yaml")
    pulse_path = cfg.resolve(cfg.paths.pulse_json)
    seed_path = Path("data/seed/pulse.json")
    if not pulse_path.is_file():
        if seed_path.is_file():
            pulse_path.parent.mkdir(parents=True, exist_ok=True)
            pulse_path.write_text(seed_path.read_text(encoding="utf-8"), encoding="utf-8")
            print(f"[serve] seeded {pulse_path} from {seed_path}")
        else:
            raise FileNotFoundError(
                f"Missing pulse artifact: {pulse_path} (and no {seed_path})"
            )

    pulse = PulseResult.model_validate_json(pulse_path.read_text(encoding="utf-8"))
    published = publish_docs_via_mcp(cfg, pulse)
    pulse.doc.id = published["document_id"]
    pulse.doc.url = published["url"]

    drafted = draft_email_via_mcp(
        cfg,
        pulse,
        doc_url=published["url"],
        to=(payload.get("to") or None),
        subject=(payload.get("subject") or None),
        body=(payload.get("body") or None),
    )
    pulse.email_draft.id = drafted["draft_id"]
    pulse_path.write_text(
        pulse.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )
    return {
        "status": "ok",
        "document_id": published["document_id"],
        "doc_url": published["url"],
        "draft_id": drafted["draft_id"],
        "to": drafted["to"],
        "subject": drafted["subject"],
    }


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        print(f"[serve] {self.address_string()} - {fmt % args}")

    def _origin_allowed(self) -> str | None:
        origin = (self.headers.get("Origin") or "").strip()
        allowed = _cors_origins()
        if "*" in allowed:
            return origin or "*"
        if origin and origin in allowed:
            return origin
        return None

    def _set_cors(self) -> None:
        allowed = self._origin_allowed()
        if allowed:
            self.send_header("Access-Control-Allow-Origin", allowed)
            self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header(
                "Access-Control-Allow-Headers",
                "Content-Type, Authorization",
            )
            self.send_header("Access-Control-Max-Age", "86400")

    def _json(self, code: int, payload: dict) -> None:
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self._set_cors()
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length") or "0")
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        if not raw:
            return {}
        data = json.loads(raw.decode("utf-8"))
        if not isinstance(data, dict):
            raise ValueError("JSON body must be an object")
        return data

    def do_OPTIONS(self) -> None:  # noqa: N802
        if self._origin_allowed() is None and (self.headers.get("Origin") or ""):
            self.send_response(403)
            self.end_headers()
            return
        self.send_response(204)
        self._set_cors()
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path in ("/", "/health"):
            self._json(200, {"status": "ok", "service": "ai-pulse-agent"})
            return
        self._json(404, {"error": "not_found"})

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/run":
            threading.Thread(target=_run_pulse, daemon=True).start()
            self._json(202, {"status": "started"})
            return
        if path == "/deliver":
            try:
                payload = self._read_json()
                result = _deliver_pulse(payload)
                self._json(200, result)
            except Exception as exc:  # noqa: BLE001 — return error to UI
                print(f"[serve] deliver failed: {exc}")
                self._json(500, {"status": "error", "error": str(exc)})
            return
        self._json(404, {"error": "not_found"})


def main() -> None:
    port = int(os.environ.get("PORT", "8080"))
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(f"[serve] listening on 0.0.0.0:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
