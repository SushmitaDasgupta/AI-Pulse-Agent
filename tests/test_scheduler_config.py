"""Phase-4 config env overrides for the weekly scheduler."""

from __future__ import annotations

import os

from src.config import apply_env_overrides, load_config


def test_require_mcp_env_override(monkeypatch) -> None:
    monkeypatch.delenv("REQUIRE_MCP", raising=False)
    cfg = load_config()
    assert cfg.langchain.require_mcp is False

    monkeypatch.setenv("REQUIRE_MCP", "true")
    cfg = load_config()
    assert cfg.langchain.require_mcp is True

    monkeypatch.setenv("REQUIRE_MCP", "0")
    cfg = load_config()
    assert cfg.langchain.require_mcp is False


def test_acquire_mode_and_max_reviews_env(monkeypatch) -> None:
    monkeypatch.setenv("ACQUIRE_MODE", "file")
    monkeypatch.setenv("ACQUIRE_MAX_REVIEWS", "1234")
    cfg = load_config()
    assert cfg.acquire.mode == "file"
    assert cfg.acquire.max_reviews == 1234


def test_apply_env_overrides_noop_when_unset(monkeypatch) -> None:
    monkeypatch.delenv("ACQUIRE_MODE", raising=False)
    monkeypatch.delenv("ACQUIRE_MAX_REVIEWS", raising=False)
    monkeypatch.delenv("REQUIRE_MCP", raising=False)
    cfg = load_config()
    before_mode = cfg.acquire.mode
    before_require = cfg.langchain.require_mcp
    again = apply_env_overrides(cfg)
    assert again.acquire.mode == before_mode
    assert again.langchain.require_mcp == before_require


def test_require_mcp_hard_fail_on_missing_doc(monkeypatch) -> None:
    """Scheduled path must exit loudly when Doc id is missing and REQUIRE_MCP=true."""
    monkeypatch.setenv("REQUIRE_MCP", "true")
    monkeypatch.delenv("GOOGLE_DOCS_DOCUMENT_ID", raising=False)
    monkeypatch.setenv("EMAIL_TO", "ops@example.com")

    from src.agent.tools.mcp_client import McpError
    from src.agent.graph import run_graph

    # Ensure config has empty docs id
    cfg = load_config()
    monkeypatch.setattr(
        "src.agent.tools.delivery.resolve_docs_document_id",
        lambda _cfg: "",
    )
    assert cfg.langchain.require_mcp is True

    try:
        run_graph(stage="publish_docs")
        raised = False
    except McpError:
        raised = True
    assert raised, "publish_docs with REQUIRE_MCP must raise when Doc id is missing"
