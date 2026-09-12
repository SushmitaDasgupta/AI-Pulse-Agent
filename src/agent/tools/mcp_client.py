"""Streamable HTTP MCP client for the Railway Google Workspace server.

Talks JSON-RPC to POST /mcp (optional Bearer / X-API-Key). No Google REST
client — Docs/Gmail I/O stays on the MCP server.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any

import httpx

from src.agent.llm import load_dotenv_if_present


DEFAULT_MCP_URL = "https://mcp-server-google-production.up.railway.app/mcp"
PROTOCOL_VERSION = "2024-11-05"


class McpError(RuntimeError):
    """Raised when the MCP session or tool call fails."""


@dataclass
class McpToolResult:
    success: bool
    payload: dict[str, Any]
    raw_text: str
    is_error: bool = False


def resolve_mcp_url(configured: str | None = None) -> str:
    load_dotenv_if_present()
    url = (configured or os.getenv("MCP_SERVER_URL") or DEFAULT_MCP_URL).strip()
    if not url.endswith("/mcp"):
        url = url.rstrip("/") + "/mcp"
    return url


def resolve_mcp_api_key(configured: str | None = None) -> str | None:
    load_dotenv_if_present()
    key = (configured or os.getenv("MCP_API_KEY") or "").strip()
    return key or None


def _auth_headers(api_key: str | None) -> dict[str, str]:
    if not api_key:
        return {}
    return {
        "Authorization": f"Bearer {api_key}",
        "X-API-Key": api_key,
    }


def _parse_jsonrpc_response(body: str, content_type: str) -> dict[str, Any]:
    text = (body or "").strip()
    if not text:
        raise McpError("Empty MCP response body")

    if "text/event-stream" in (content_type or "") or text.startswith("event:"):
        data_lines: list[str] = []
        for line in text.splitlines():
            if line.startswith("data:"):
                data_lines.append(line[5:].lstrip())
        if not data_lines:
            raise McpError(f"No SSE data frames in MCP response: {text[:300]}")
        # Last data frame is typically the JSON-RPC result.
        text = data_lines[-1]

    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise McpError(f"Invalid MCP JSON: {text[:300]}") from exc

    if not isinstance(payload, dict):
        raise McpError(f"Unexpected MCP payload type: {type(payload)}")
    if "error" in payload and payload["error"]:
        err = payload["error"]
        raise McpError(f"MCP JSON-RPC error: {err}")
    return payload


def _extract_tool_payload(result: dict[str, Any]) -> McpToolResult:
    """Parse MCP tools/call result → server JSON envelope when present."""
    content = result.get("content") or []
    texts: list[str] = []
    for block in content:
        if isinstance(block, dict) and block.get("type") == "text":
            texts.append(str(block.get("text") or ""))
        elif isinstance(block, dict) and "text" in block:
            texts.append(str(block["text"]))
    raw = "\n".join(t for t in texts if t).strip() or json.dumps(result)
    is_error = bool(result.get("isError"))

    payload: dict[str, Any]
    try:
        parsed = json.loads(raw)
        payload = parsed if isinstance(parsed, dict) else {"raw": parsed}
    except json.JSONDecodeError:
        payload = {"message": raw}

    success = bool(payload.get("success", not is_error))
    if is_error or payload.get("success") is False:
        success = False
    return McpToolResult(
        success=success,
        payload=payload,
        raw_text=raw,
        is_error=is_error or not success,
    )


class McpHttpClient:
    """Minimal sync Streamable HTTP MCP client (initialize → tools/call)."""

    def __init__(
        self,
        url: str | None = None,
        api_key: str | None = None,
        *,
        timeout: float = 60.0,
    ) -> None:
        self.url = resolve_mcp_url(url)
        self.api_key = resolve_mcp_api_key(api_key)
        self.timeout = timeout
        self._session_id: str | None = None
        self._request_id = 0

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    def _headers(self) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            **_auth_headers(self.api_key),
        }
        if self._session_id:
            headers["Mcp-Session-Id"] = self._session_id
        return headers

    def _post(self, message: dict[str, Any]) -> tuple[httpx.Response, dict[str, Any] | None]:
        # trust_env=False avoids corporate/sandbox HTTP_PROXY tunnels that break Railway HTTPS.
        with httpx.Client(
            timeout=self.timeout, follow_redirects=True, trust_env=False
        ) as client:
            response = client.post(self.url, headers=self._headers(), json=message)

        session = response.headers.get("mcp-session-id") or response.headers.get(
            "Mcp-Session-Id"
        )
        if session:
            self._session_id = session

        if response.status_code == 401:
            raise McpError(
                "MCP unauthorized (401). Set MCP_API_KEY to match the Railway server."
            )
        if response.status_code >= 400:
            raise McpError(
                f"MCP HTTP {response.status_code}: {response.text[:400]}"
            )

        # Notifications may return 202/204 with empty body.
        if response.status_code in (202, 204) or not response.content:
            return response, None

        parsed = _parse_jsonrpc_response(
            response.text, response.headers.get("content-type", "")
        )
        return response, parsed

    def initialize(self) -> dict[str, Any]:
        _, parsed = self._post(
            {
                "jsonrpc": "2.0",
                "id": self._next_id(),
                "method": "initialize",
                "params": {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {},
                    "clientInfo": {"name": "ai-review-pulsator", "version": "0.1.0"},
                },
            }
        )
        if parsed is None:
            raise McpError("MCP initialize returned empty body")
        # Required notification after initialize.
        self._post(
            {
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
            }
        )
        return parsed.get("result") or parsed

    def list_tools(self) -> list[dict[str, Any]]:
        if not self._session_id:
            self.initialize()
        _, parsed = self._post(
            {
                "jsonrpc": "2.0",
                "id": self._next_id(),
                "method": "tools/list",
                "params": {},
            }
        )
        if parsed is None:
            raise McpError("tools/list returned empty body")
        result = parsed.get("result") or {}
        tools = result.get("tools") or []
        return [t for t in tools if isinstance(t, dict)]

    def call_tool(self, name: str, arguments: dict[str, Any]) -> McpToolResult:
        if not self._session_id:
            self.initialize()
        _, parsed = self._post(
            {
                "jsonrpc": "2.0",
                "id": self._next_id(),
                "method": "tools/call",
                "params": {"name": name, "arguments": arguments},
            }
        )
        if parsed is None:
            raise McpError(f"tools/call {name} returned empty body")
        result = parsed.get("result")
        if not isinstance(result, dict):
            raise McpError(f"tools/call {name} missing result: {parsed}")
        tool_result = _extract_tool_payload(result)
        if not tool_result.success:
            err = tool_result.payload.get("error") or tool_result.raw_text
            raise McpError(f"MCP tool {name} failed: {err}")
        return tool_result


_DOC_ID_RE = re.compile(r"/document/d/([a-zA-Z0-9_-]+)")


def docs_url_for_id(document_id: str) -> str:
    return f"https://docs.google.com/document/d/{document_id}/edit"


def extract_document_id(value: str) -> str:
    """Accept a bare document id or a full Google Docs URL."""
    text = (value or "").strip()
    if not text:
        return ""
    match = _DOC_ID_RE.search(text)
    if match:
        return match.group(1)
    return text
