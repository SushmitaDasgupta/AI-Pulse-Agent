"""Phase-3 MCP delivery unit tests (mocked HTTP — no live Railway)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from src.agent.schemas import (
    ActionRecord,
    DateWindow,
    PulseResult,
    TopThemeSummary,
)
from src.agent.tools.delivery import (
    build_docs_append_content,
    build_email_body,
    draft_email_via_mcp,
    publish_docs_via_mcp,
)
from src.agent.tools.mcp_client import (
    McpError,
    McpHttpClient,
    _extract_tool_payload,
    _parse_jsonrpc_response,
    docs_url_for_id,
    extract_document_id,
)
from src.config import load_config


def _pulse() -> PulseResult:
    return PulseResult(
        product="ChatGPT (Android)",
        window=DateWindow(start="2026-08-26", end="2026-09-09"),
        top_themes=[
            TopThemeSummary(
                label="Paywall / limits / upgrade friction",
                summary="Free-tier chat caps and upgrade nags.",
                review_count=555,
            ),
            TopThemeSummary(
                label="Answer quality / misunderstandings",
                summary="Wrong answers and flip-flops.",
                review_count=311,
            ),
        ],
        actions=[
            ActionRecord(
                title="Clarify free-tier limits before users hit the wall",
                theme="Paywall / limits / upgrade friction",
            ),
            ActionRecord(
                title="Reduce confident-wrong answers and flip-flops",
                theme="Answer quality / misunderstandings",
            ),
        ],
        word_count=42,
        markdown=(
            "# Pulse\n\n**Window:** 2026-08-26 → 2026-09-09 · "
            "**Cleaned reviews:** 9,428\n"
        ),
    )


def test_extract_document_id_from_url_and_bare() -> None:
    assert (
        extract_document_id("https://docs.google.com/document/d/AbC123_x/edit")
        == "AbC123_x"
    )
    assert extract_document_id("AbC123_x") == "AbC123_x"


def test_parse_sse_jsonrpc() -> None:
    body = (
        "event: message\n"
        'data: {"jsonrpc":"2.0","id":1,"result":{"ok":true}}\n\n'
    )
    parsed = _parse_jsonrpc_response(body, "text/event-stream")
    assert parsed["result"]["ok"] is True


def test_extract_tool_payload_success_envelope() -> None:
    result = {
        "content": [
            {
                "type": "text",
                "text": json.dumps(
                    {
                        "success": True,
                        "message": "ok",
                        "documentId": "doc1",
                    }
                ),
            }
        ]
    }
    out = _extract_tool_payload(result)
    assert out.success is True
    assert out.payload["documentId"] == "doc1"


def test_extract_tool_payload_failure_envelope() -> None:
    result = {
        "isError": True,
        "content": [
            {
                "type": "text",
                "text": json.dumps(
                    {
                        "success": False,
                        "error": {"code": "DOCUMENT_NOT_FOUND", "message": "missing"},
                    }
                ),
            }
        ],
    }
    out = _extract_tool_payload(result)
    assert out.success is False


def test_build_email_includes_doc_link() -> None:
    body = build_email_body(
        _pulse(),
        "https://docs.google.com/document/d/x/edit",
        iso_week="2026-W37",
    )
    assert "ChatGPT (Android) Play Pulse — 2026-W37" in body
    assert "26 Aug → 9 Sep 2026" in body
    assert "9,428 cleaned reviews" in body
    assert "Top themes" in body
    assert "1. Paywall / limits / upgrade friction (n=555)" in body
    assert "Free-tier chat caps and upgrade nags." in body
    assert "Suggested actions" in body
    assert "Clarify free-tier limits before users hit the wall" in body
    assert "Read the full pulse (quotes + detail):" in body
    assert "https://docs.google.com/document/d/x/edit" in body
    assert "Draft only — review in Gmail" in body


def test_publish_and_draft_via_mocked_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = load_config()
    monkeypatch.setenv("GOOGLE_DOCS_DOCUMENT_ID", "DocId123")
    monkeypatch.setattr(cfg.mcp, "docs_document_id", "DocId123")
    monkeypatch.setenv("EMAIL_TO", "ops@example.com")
    monkeypatch.setattr(cfg, "email_to", "you@example.com")

    calls: list[tuple[str, dict[str, Any]]] = []

    class FakeClient(McpHttpClient):
        def __init__(self) -> None:  # noqa: D107
            pass

        def call_tool(self, name: str, arguments: dict[str, Any]):  # type: ignore[override]
            from src.agent.tools.mcp_client import McpToolResult

            calls.append((name, arguments))
            if name == "google_docs_append_content":
                return McpToolResult(
                    success=True,
                    payload={
                        "success": True,
                        "documentId": arguments["documentId"],
                        "message": "appended",
                    },
                    raw_text="{}",
                )
            if name == "gmail_draft_email":
                return McpToolResult(
                    success=True,
                    payload={"success": True, "draftId": "r-draft-1", "message": "drafted"},
                    raw_text="{}",
                )
            raise AssertionError(name)

    pulse = _pulse()
    published = publish_docs_via_mcp(cfg, pulse, client=FakeClient())
    assert published["document_id"] == "DocId123"
    assert published["url"] == docs_url_for_id("DocId123")
    appended = build_docs_append_content(pulse, iso_week="2026-W37")
    assert "2026-W37" in appended and "Cleaned reviews" in appended

    drafted = draft_email_via_mcp(
        cfg, pulse, doc_url=published["url"], client=FakeClient()
    )
    assert drafted["draft_id"] == "r-draft-1"
    assert calls[0][0] == "google_docs_append_content"
    assert calls[1][0] == "gmail_draft_email"
    assert "gmail_send_email" not in {c[0] for c in calls}


def test_publish_requires_document_id(monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = load_config()
    # Empty string wins over .env because load_dotenv does not override existing keys.
    monkeypatch.setenv("GOOGLE_DOCS_DOCUMENT_ID", "")
    monkeypatch.setattr(cfg.mcp, "docs_document_id", "")
    with pytest.raises(McpError, match="Missing Google Doc id"):
        publish_docs_via_mcp(cfg, _pulse(), client=McpHttpClient.__new__(McpHttpClient))
