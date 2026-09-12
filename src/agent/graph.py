"""LangGraph weekly-pulse graph: P1 ingest + P2 LangChain pulse + P3 MCP delivery."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from src.agent.chains.compose import run_compose_chain, write_pulse
from src.agent.chains.select import load_selection, run_select_chain, write_selection
from src.agent.chains.theme import load_themes, run_theme_chain, write_themes
from src.agent.corpus import load_cleaned
from src.agent.schemas import PulseResult
from src.agent.tools.delivery import (
    draft_email_via_mcp,
    mcp_ready_for_publish,
    publish_docs_via_mcp,
)
from src.agent.tools.mcp_client import McpError
from src.agent.validators import validate_pulse_artifacts
from src.config import AppConfig, load_config
from src.ingest.pipeline import run_acquire, run_normalize, run_scrub


class PulsatorState(TypedDict, total=False):
    config_path: str
    stage_filter: str | None
    raw_path: str
    normalized_path: str
    cleaned_path: str
    review_count: int
    messages: list[str]
    themes_path: str
    selection_path: str
    pulse_md_path: str
    pulse_json_path: str
    run_log_path: str
    skipped: list[str]
    validation_errors: list[str]
    doc_id: str
    doc_url: str
    email_draft_id: str


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _append_log(path: Path, line: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line.rstrip() + "\n")


def _load_cfg(state: PulsatorState) -> AppConfig:
    return load_config(state.get("config_path"))


def _stage_matches(state: PulsatorState, *ids: str) -> bool:
    stage = state.get("stage_filter")
    if not stage:
        return True
    return stage in ids


def _skip(state: PulsatorState, node_id: str) -> dict[str, Any]:
    skipped = list(state.get("skipped") or [])
    skipped.append(node_id)
    return {"skipped": skipped}


def acquire_node(state: PulsatorState) -> dict[str, Any]:
    if not _stage_matches(state, "acquire", "ingest"):
        return _skip(state, "acquire")

    cfg = _load_cfg(state)
    result = run_acquire(cfg)
    run_log = cfg.resolve(cfg.paths.run_log)
    for message in result.messages or []:
        _append_log(run_log, f"{_now_iso()} {message}")
    messages = list(state.get("messages") or [])
    messages.extend(result.messages or [])
    return {
        "raw_path": str(result.raw_path) if result.raw_path else None,
        "review_count": len(result.raw.reviews) if result.raw else 0,
        "run_log_path": str(run_log),
        "messages": messages,
    }


def normalize_node(state: PulsatorState) -> dict[str, Any]:
    if not _stage_matches(state, "normalize", "ingest"):
        return _skip(state, "normalize")

    cfg = _load_cfg(state)
    raw_path = Path(state["raw_path"]) if state.get("raw_path") else None
    result = run_normalize(cfg, raw_path=raw_path)
    run_log = cfg.resolve(cfg.paths.run_log)
    for message in result.messages or []:
        _append_log(run_log, f"{_now_iso()} {message}")
    messages = list(state.get("messages") or [])
    messages.extend(result.messages or [])
    return {
        "raw_path": str(result.raw_path) if result.raw_path else state.get("raw_path"),
        "normalized_path": str(result.normalized_path) if result.normalized_path else None,
        "review_count": len(result.normalized.reviews) if result.normalized else 0,
        "run_log_path": str(run_log),
        "messages": messages,
    }


def scrub_node(state: PulsatorState) -> dict[str, Any]:
    if not _stage_matches(state, "scrub", "ingest"):
        return _skip(state, "scrub")

    cfg = _load_cfg(state)
    normalized_path = Path(state["normalized_path"]) if state.get("normalized_path") else None
    result = run_scrub(cfg, normalized_path=normalized_path)
    run_log = cfg.resolve(cfg.paths.run_log)
    for message in result.messages or []:
        _append_log(run_log, f"{_now_iso()} {message}")
    if result.cleaned:
        counts = result.cleaned.counts
        _append_log(
            run_log,
            f"{_now_iso()} ingest summary fetched={counts.get('fetched', 0)} "
            f"in_window={counts.get('in_window', 0)} cleaned={counts.get('cleaned', 0)} "
            f"window={result.cleaned.window.start}..{result.cleaned.window.end} "
            f"app_id={result.cleaned.app_id} url={cfg.play_url}",
        )
    messages = list(state.get("messages") or [])
    messages.extend(result.messages or [])
    return {
        "normalized_path": str(result.normalized_path)
        if result.normalized_path
        else state.get("normalized_path"),
        "cleaned_path": str(result.cleaned_path) if result.cleaned_path else None,
        "review_count": len(result.cleaned.reviews) if result.cleaned else 0,
        "run_log_path": str(run_log),
        "messages": messages,
    }


def theme_node(state: PulsatorState) -> dict[str, Any]:
    if not _stage_matches(state, "theme", "pulse"):
        return _skip(state, "theme")

    cfg = _load_cfg(state)
    run_log = cfg.resolve(cfg.paths.run_log)
    themes, _assignments, stats = run_theme_chain(cfg)
    out_path = write_themes(cfg, themes)
    classify = cfg.langchain.classify
    generate = cfg.langchain.generate
    _append_log(run_log, f"{_now_iso()} {stats.log_line()}")
    _append_log(
        run_log,
        f"{_now_iso()} llm classify={classify.provider}/{classify.model} "
        f"generate={generate.provider}/{generate.model}",
    )
    _append_log(
        run_log,
        f"{_now_iso()} theme wrote {out_path} themes={len(themes.themes)} "
        f"labels={[t.label for t in themes.themes]}",
    )
    messages = list(state.get("messages") or [])
    messages.append(
        f"theme: {len(themes.themes)} themes from {stats.n} cleaned reviews → {out_path}"
    )
    return {
        "themes_path": str(out_path),
        "cleaned_path": str(cfg.resolve(cfg.paths.cleaned_reviews)),
        "review_count": stats.n,
        "run_log_path": str(run_log),
        "messages": messages,
    }


def select_node(state: PulsatorState) -> dict[str, Any]:
    if not _stage_matches(state, "select", "pulse"):
        return _skip(state, "select")

    cfg = _load_cfg(state)
    run_log = cfg.resolve(cfg.paths.run_log)
    themes = None
    if state.get("themes_path"):
        themes = load_themes(cfg, Path(state["themes_path"]))
    elif cfg.resolve(cfg.paths.themes).exists():
        themes = load_themes(cfg)

    selection = run_select_chain(cfg, themes=themes)
    out_path = write_selection(cfg, selection)
    _append_log(
        run_log,
        f"{_now_iso()} select wrote {out_path} "
        f"top={[t.label for t in selection.top_themes]} "
        f"quotes={len(selection.quotes)} actions={len(selection.actions)}",
    )
    messages = list(state.get("messages") or [])
    messages.append(
        f"select: top {len(selection.top_themes)} themes, "
        f"{len(selection.quotes)} quotes, {len(selection.actions)} actions → {out_path}"
    )
    return {"selection_path": str(out_path), "run_log_path": str(run_log), "messages": messages}


def compose_node(state: PulsatorState) -> dict[str, Any]:
    if not _stage_matches(state, "compose", "pulse"):
        return _skip(state, "compose")

    cfg = _load_cfg(state)
    run_log = cfg.resolve(cfg.paths.run_log)
    selection = None
    themes = None
    if state.get("selection_path"):
        selection = load_selection(cfg, Path(state["selection_path"]))
    elif cfg.resolve(cfg.paths.selection).exists():
        selection = load_selection(cfg)
    if state.get("themes_path"):
        themes = load_themes(cfg, Path(state["themes_path"]))
    elif cfg.resolve(cfg.paths.themes).exists():
        themes = load_themes(cfg)

    pulse = run_compose_chain(cfg, selection=selection, themes=themes)
    md_path, json_path = write_pulse(cfg, pulse)
    _append_log(
        run_log,
        f"{_now_iso()} compose wrote {md_path} {json_path} words={pulse.word_count}",
    )
    messages = list(state.get("messages") or [])
    messages.append(f"compose: pulse words={pulse.word_count} → {md_path}")
    return {
        "pulse_md_path": str(md_path),
        "pulse_json_path": str(json_path),
        "run_log_path": str(run_log),
        "messages": messages,
    }


def validate_node(state: PulsatorState) -> dict[str, Any]:
    if not _stage_matches(state, "validate", "pulse"):
        return _skip(state, "validate")

    cfg = _load_cfg(state)
    run_log = cfg.resolve(cfg.paths.run_log)
    export = load_cleaned(cfg)
    themes = load_themes(cfg)
    selection = load_selection(cfg)
    pulse = PulseResult.model_validate_json(
        cfg.resolve(cfg.paths.pulse_json).read_text(encoding="utf-8")
    )
    errors = validate_pulse_artifacts(
        themes,
        selection,
        pulse,
        cleaned_texts=[r.text for r in export.reviews],
        max_themes=cfg.max_themes,
        max_words=cfg.max_pulse_words,
    )
    if errors:
        for err in errors:
            _append_log(run_log, f"{_now_iso()} validate FAIL {err}")
        messages = list(state.get("messages") or [])
        messages.append(f"validate: FAILED ({len(errors)} errors)")
        raise ValueError("Pulse validation failed:\n- " + "\n- ".join(errors))

    _append_log(run_log, f"{_now_iso()} validate ok themes={len(themes.themes)} words={pulse.word_count}")
    messages = list(state.get("messages") or [])
    messages.append("validate: passed")
    return {"validation_errors": [], "run_log_path": str(run_log), "messages": messages}


def _load_pulse(cfg: AppConfig, state: PulsatorState) -> PulseResult:
    path = Path(state["pulse_json_path"]) if state.get("pulse_json_path") else cfg.resolve(
        cfg.paths.pulse_json
    )
    return PulseResult.model_validate_json(path.read_text(encoding="utf-8"))


def _persist_pulse_delivery(cfg: AppConfig, pulse: PulseResult) -> Path:
    path = cfg.resolve(cfg.paths.pulse_json)
    path.write_text(pulse.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return path


def publish_node(state: PulsatorState) -> dict[str, Any]:
    if not _stage_matches(state, "publish", "publish_docs"):
        return _skip(state, "publish")

    cfg = _load_cfg(state)
    run_log = cfg.resolve(cfg.paths.run_log)
    messages = list(state.get("messages") or [])
    ready, reason = mcp_ready_for_publish(cfg)

    if not ready:
        msg = f"publish: skipped ({reason})"
        _append_log(run_log, f"{_now_iso()} {msg}")
        messages.append(msg)
        if cfg.langchain.require_mcp:
            raise McpError(msg)
        return {"messages": messages, "run_log_path": str(run_log)}

    try:
        pulse = _load_pulse(cfg, state)
        published = publish_docs_via_mcp(cfg, pulse)
        pulse.doc.id = published["document_id"]
        pulse.doc.url = published["url"]
        _persist_pulse_delivery(cfg, pulse)
        _append_log(
            run_log,
            f"{_now_iso()} publish ok tool=google_docs_append_content "
            f"doc_id={published['document_id']} url={published['url']}",
        )
        messages.append(f"publish: appended pulse → {published['url']}")
        return {
            "messages": messages,
            "run_log_path": str(run_log),
            "doc_id": published["document_id"],
            "doc_url": published["url"],
            "pulse_json_path": str(cfg.resolve(cfg.paths.pulse_json)),
        }
    except Exception as exc:
        _append_log(run_log, f"{_now_iso()} publish FAIL {exc}")
        messages.append(f"publish: FAILED ({exc})")
        if cfg.langchain.require_mcp:
            raise
        return {"messages": messages, "run_log_path": str(run_log)}


def draft_email_node(state: PulsatorState) -> dict[str, Any]:
    if not _stage_matches(state, "draft_email"):
        return _skip(state, "draft_email")

    cfg = _load_cfg(state)
    run_log = cfg.resolve(cfg.paths.run_log)
    messages = list(state.get("messages") or [])

    try:
        pulse = _load_pulse(cfg, state)
    except Exception as exc:
        msg = f"draft_email: skipped (no pulse.json: {exc})"
        _append_log(run_log, f"{_now_iso()} {msg}")
        messages.append(msg)
        if cfg.langchain.require_mcp:
            raise McpError(msg) from exc
        return {"messages": messages, "run_log_path": str(run_log)}

    doc_url = state.get("doc_url") or (pulse.doc.url if pulse.doc else None)
    try:
        drafted = draft_email_via_mcp(cfg, pulse, doc_url=doc_url)
        pulse.email_draft.id = drafted["draft_id"]
        if doc_url and not pulse.doc.url:
            pulse.doc.url = doc_url
        _persist_pulse_delivery(cfg, pulse)
        _append_log(
            run_log,
            f"{_now_iso()} draft_email ok tool=gmail_draft_email "
            f"draft_id={drafted['draft_id']} to={drafted['to']}",
        )
        messages.append(
            f"draft_email: Gmail draft {drafted['draft_id']} → {drafted['to']}"
        )
        return {
            "messages": messages,
            "run_log_path": str(run_log),
            "email_draft_id": drafted["draft_id"],
            "pulse_json_path": str(cfg.resolve(cfg.paths.pulse_json)),
        }
    except Exception as exc:
        _append_log(run_log, f"{_now_iso()} draft_email FAIL {exc}")
        messages.append(f"draft_email: FAILED ({exc})")
        if cfg.langchain.require_mcp:
            raise
        return {"messages": messages, "run_log_path": str(run_log)}


def build_graph() -> Any:
    """Build the LangGraph weekly-pulse graph."""
    graph = StateGraph(PulsatorState)
    graph.add_node("acquire", acquire_node)
    graph.add_node("normalize", normalize_node)
    graph.add_node("scrub", scrub_node)
    graph.add_node("theme", theme_node)
    graph.add_node("select", select_node)
    graph.add_node("compose", compose_node)
    graph.add_node("validate", validate_node)
    graph.add_node("publish", publish_node)
    graph.add_node("draft_email", draft_email_node)

    graph.add_edge(START, "acquire")
    graph.add_edge("acquire", "normalize")
    graph.add_edge("normalize", "scrub")
    graph.add_edge("scrub", "theme")
    graph.add_edge("theme", "select")
    graph.add_edge("select", "compose")
    graph.add_edge("compose", "validate")
    graph.add_edge("validate", "publish")
    graph.add_edge("publish", "draft_email")
    graph.add_edge("draft_email", END)
    return graph.compile()


def run_graph(
    config_path: str | None = None,
    stage: str | None = None,
) -> PulsatorState:
    """Execute the graph end-to-end (or filter by stage id)."""
    app = build_graph()
    initial: PulsatorState = {
        "messages": [],
        "skipped": [],
    }
    if config_path:
        initial["config_path"] = config_path
    if stage:
        initial["stage_filter"] = stage
    result = app.invoke(initial)
    return result  # type: ignore[return-value]


__all__ = ["build_graph", "run_graph", "PulsatorState"]
