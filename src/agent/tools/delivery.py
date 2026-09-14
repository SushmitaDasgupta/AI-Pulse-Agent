"""P3 delivery tools: LangChain-facing wrappers → Railway Google MCP tools.

MCP tools used (server: google-workspace-mcp):
  - google_docs_append_content  (rolling doc — server cannot create docs)
  - gmail_draft_email           (draft only; never gmail_send_email)
"""

from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from typing import Any

from src.agent.llm import load_dotenv_if_present
from src.agent.schemas import PulseResult
from src.agent.tools.mcp_client import (
    McpError,
    McpHttpClient,
    docs_url_for_id,
    extract_document_id,
    resolve_mcp_api_key,
    resolve_mcp_url,
)
from src.config import AppConfig


def resolve_docs_document_id(cfg: AppConfig) -> str:
    load_dotenv_if_present()
    raw = (
        os.getenv("GOOGLE_DOCS_DOCUMENT_ID")
        or cfg.mcp.docs_document_id
        or ""
    ).strip()
    return extract_document_id(raw)


def resolve_email_to(cfg: AppConfig) -> str:
    """Prefer EMAIL_TO / email_to from .env; fall back to config.yaml."""
    load_dotenv_if_present()
    return (
        os.getenv("EMAIL_TO")
        or os.getenv("email_to")
        or cfg.email_to
        or ""
    ).strip()


def iso_week_label(now: datetime | None = None) -> str:
    stamp = now or datetime.now(timezone.utc)
    iso = stamp.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def build_docs_append_content(pulse: PulseResult, *, iso_week: str) -> str:
    header = f"\n\n---\n# {iso_week}\n"
    body = (pulse.markdown or "").strip()
    if not body:
        raise McpError("pulse markdown is empty; refuse to publish")
    return f"{header}{body}\n"


def _format_day_month(iso_date: str) -> str:
    """Format YYYY-MM-DD as '26 Aug' (no leading zero)."""
    try:
        stamp = datetime.strptime(iso_date[:10], "%Y-%m-%d")
    except ValueError:
        return iso_date
    return f"{stamp.day} {stamp.strftime('%b')}"


def _format_window(pulse: PulseResult) -> str:
    if not pulse.window:
        return "?"
    start_raw = pulse.window.start
    end_raw = pulse.window.end
    start = _format_day_month(start_raw)
    end = _format_day_month(end_raw)
    year = ""
    try:
        year = f" {datetime.strptime(end_raw[:10], '%Y-%m-%d').year}"
    except ValueError:
        year = ""
    return f"{start} → {end}{year}"


def _cleaned_review_count(pulse: PulseResult) -> int | None:
    """Best-effort parse from pulse markdown header (not on PulseResult schema)."""
    match = re.search(
        r"Cleaned reviews:\*?\*?\s*([\d,]+)",
        pulse.markdown or "",
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    try:
        return int(match.group(1).replace(",", ""))
    except ValueError:
        return None


def build_email_body(
    pulse: PulseResult,
    doc_url: str | None,
    *,
    iso_week: str | None = None,
) -> str:
    """Executive-style Gmail draft body (plain text; draft-only footer)."""
    week = iso_week or iso_week_label()
    product = (pulse.product or "ChatGPT (Android)").strip()
    window = _format_window(pulse)
    cleaned = _cleaned_review_count(pulse)
    meta_bits = [f"Window: {window}"]
    if cleaned is not None:
        meta_bits.append(f"{cleaned:,} cleaned reviews")
    if pulse.word_count:
        meta_bits.append(f"{pulse.word_count} words")

    lines = [
        f"{product} Play Pulse — {week}",
        "",
        "Weekly signal from Android Google Play reviews.",
        " · ".join(meta_bits),
        "",
        "Top themes",
    ]
    themes = list(pulse.top_themes[:3])
    if not themes:
        lines.append("(none)")
    else:
        for i, theme in enumerate(themes, start=1):
            n = f" (n={theme.review_count:,})" if theme.review_count else ""
            lines.append(f"{i}. {theme.label}{n}")
            summary = (theme.summary or "").strip()
            if summary:
                lines.append(f"   {summary}")

    lines.extend(["", "Suggested actions"])
    actions = list(pulse.actions[:3])
    if not actions:
        lines.append("(none)")
    else:
        for i, action in enumerate(actions, start=1):
            lines.append(f"{i}. {action.title}")

    lines.append("")
    if doc_url:
        lines.extend(
            [
                "Read the full pulse (quotes + detail):",
                doc_url,
            ]
        )
    else:
        lines.append("(Doc URL unavailable — see out/pulse.md locally.)")

    lines.extend(
        [
            "",
            "—",
            "Draft only — review in Gmail, then send when ready.",
            "AI Review Pulsator",
        ]
    )
    return "\n".join(lines)


def publish_docs_via_mcp(
    cfg: AppConfig,
    pulse: PulseResult,
    *,
    client: McpHttpClient | None = None,
) -> dict[str, Any]:
    """Append pulse markdown to the configured Google Doc via MCP."""
    document_id = resolve_docs_document_id(cfg)
    if not document_id:
        raise McpError(
            "Missing Google Doc id. Set GOOGLE_DOCS_DOCUMENT_ID or "
            "mcp.docs_document_id (MCP server only appends to an existing doc)."
        )

    week = iso_week_label()
    content = build_docs_append_content(pulse, iso_week=week)
    mcp = client or McpHttpClient(
        url=cfg.mcp.url or None,
        api_key=cfg.mcp.api_key or None,
    )
    result = mcp.call_tool(
        "google_docs_append_content",
        {"documentId": document_id, "content": content},
    )
    doc_id = str(result.payload.get("documentId") or document_id)
    return {
        "document_id": doc_id,
        "url": docs_url_for_id(doc_id),
        "message": result.payload.get("message"),
        "tool": "google_docs_append_content",
    }


def draft_email_via_mcp(
    cfg: AppConfig,
    pulse: PulseResult,
    *,
    doc_url: str | None = None,
    client: McpHttpClient | None = None,
) -> dict[str, Any]:
    """Create an unsent Gmail draft via MCP (never sends)."""
    to_addr = resolve_email_to(cfg)
    if not to_addr or to_addr == "you@example.com":
        raise McpError(
            "Set EMAIL_TO in .env (or email_to in config.yaml) to a real address "
            "before drafting."
        )

    week = iso_week_label()
    subject_tmpl = cfg.mcp.email_subject_template or cfg.docs_title_template
    subject = subject_tmpl.format(iso_week=week)
    body = build_email_body(pulse, doc_url, iso_week=week)
    mcp = client or McpHttpClient(
        url=cfg.mcp.url or None,
        api_key=cfg.mcp.api_key or None,
    )
    result = mcp.call_tool(
        "gmail_draft_email",
        {
            "to": [to_addr],
            "subject": subject,
            "body": body,
        },
    )
    draft_id = str(result.payload.get("draftId") or "")
    if not draft_id:
        raise McpError(f"gmail_draft_email succeeded without draftId: {result.payload}")
    return {
        "draft_id": draft_id,
        "to": to_addr,
        "subject": subject,
        "message": result.payload.get("message"),
        "tool": "gmail_draft_email",
    }


def mcp_configured(cfg: AppConfig) -> bool:
    """True when URL is set (API key optional if server allows open /mcp)."""
    try:
        resolve_mcp_url(cfg.mcp.url or None)
        return True
    except Exception:
        return False


def mcp_ready_for_publish(cfg: AppConfig) -> tuple[bool, str]:
    if not mcp_configured(cfg):
        return False, "MCP URL not configured"
    if not resolve_docs_document_id(cfg):
        return False, "GOOGLE_DOCS_DOCUMENT_ID / mcp.docs_document_id missing"
    # Surface missing API key only as soft note — server may be open.
    _ = resolve_mcp_api_key(cfg.mcp.api_key or None)
    return True, "ok"
