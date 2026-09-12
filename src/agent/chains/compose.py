"""Compose chain: ≤250-word pulse markdown + pulse.json."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from src.agent.chains.select import load_selection
from src.agent.chains.theme import load_themes
from src.agent.corpus import corpus_stats, load_cleaned
from src.agent.llm import get_generate_model
from src.agent.schemas import PulseResult, SelectionResult, ThemesResult
from src.config import AppConfig


def _stakeholder_body(
    *,
    product: str,
    date_min: str,
    date_max: str,
    n: int,
    undercovered: bool,
    lookback_start: str | None,
    lookback_end: str | None,
    selection: SelectionResult,
) -> str:
    theme_lines = []
    for i, theme in enumerate(selection.top_themes, start=1):
        summary = theme.summary.strip()
        if len(summary.split()) > 16:
            summary = " ".join(summary.split()[:16]).rstrip(".,;") + "…"
        theme_lines.append(
            f"{i}. **{theme.label}** (n={theme.review_count}) — {summary}"
        )

    quote_lines = []
    for i, quote in enumerate(selection.quotes, start=1):
        quote_lines.append(f'{i}. "{quote.text}"')

    action_lines = []
    for i, action in enumerate(selection.actions, start=1):
        rationale = action.rationale.strip()
        if len(rationale.split()) > 18:
            rationale = " ".join(rationale.split()[:18]).rstrip(".,;") + "…"
        action_lines.append(f"{i}. **{action.title}** — {rationale}")

    caveat = ""
    if undercovered and lookback_start and lookback_end:
        caveat = (
            f" Note: full {lookback_start}–{lookback_end} lookback not covered yet."
        )
    elif undercovered:
        caveat = " Note: full 8–12 week lookback not covered yet."

    body = (
        f"# {product} Play Pulse\n\n"
        f"**Window:** {date_min} → {date_max} · **Cleaned reviews:** {n:,}.{caveat}\n\n"
        f"## Top themes\n"
        + "\n".join(theme_lines)
        + "\n\n## User quotes\n"
        + "\n".join(quote_lines)
        + "\n\n## Action ideas\n"
        + "\n".join(action_lines)
        + "\n"
    )
    return body


def _word_count(text: str) -> int:
    return len(text.split())


def shorten_markdown(markdown: str, max_words: int) -> str:
    """Deterministic shorten: trim theme/action rationales then truncate."""
    if _word_count(markdown) <= max_words:
        return markdown
    lines = markdown.splitlines()
    out: list[str] = []
    for line in lines:
        if " — " in line and line.lstrip()[:1].isdigit():
            head, _, _tail = line.partition(" — ")
            line = head
        if ": " in line and line.strip().startswith(("1.", "2.", "3.")) and "Action" not in line[:20]:
            # keep action titles; shorten rationales already handled via —
            pass
        out.append(line)
    text = "\n".join(out)
    if _word_count(text) <= max_words:
        return text
    words = text.split()
    return " ".join(words[:max_words])


def run_compose_chain(
    cfg: AppConfig,
    selection: SelectionResult | None = None,
    themes: ThemesResult | None = None,
) -> PulseResult:
    export = load_cleaned(cfg)
    stats = corpus_stats(export)
    selection = selection or load_selection(cfg)
    themes = themes or load_themes(cfg)

    date_min = stats.date_min or (themes.window.start if themes.window else "unknown")
    date_max = stats.date_max or (themes.window.end if themes.window else "unknown")

    markdown = _stakeholder_body(
        product="ChatGPT (Android)",
        date_min=date_min,
        date_max=date_max,
        n=stats.n,
        undercovered=stats.undercovered,
        lookback_start=stats.lookback_start,
        lookback_end=stats.lookback_end,
        selection=selection,
    )
    markdown = _maybe_llm_compose(cfg, markdown, selection, stats.n, date_min, date_max)
    if _word_count(markdown) > cfg.max_pulse_words:
        markdown = _maybe_llm_shorten(cfg, markdown, cfg.max_pulse_words)
    if _word_count(markdown) > cfg.max_pulse_words:
        markdown = shorten_markdown(markdown, cfg.max_pulse_words)

    pulse = PulseResult(
        product="ChatGPT (Android)",
        app_id=export.app_id,
        window=themes.window,
        generated_at=datetime.now(timezone.utc),
        top_themes=selection.top_themes,
        quotes=selection.quotes,
        actions=selection.actions,
        word_count=_word_count(markdown),
        markdown=markdown,
    )
    return pulse


def _maybe_llm_compose(
    cfg: AppConfig,
    fallback_md: str,
    selection: SelectionResult,
    n: int,
    date_min: str,
    date_max: str,
) -> str:
    model = get_generate_model(cfg)
    prompt_path = cfg.resolve(cfg.paths.prompts_dir) / "compose.txt"
    if model is None or not prompt_path.exists():
        return fallback_md
    try:
        from langchain_core.messages import HumanMessage, SystemMessage

        payload = (
            f"Corpus: {n} cleaned English reviews, {date_min} to {date_max}.\n"
            f"Top themes: {selection.model_dump_json()}\n"
            "Write the stakeholder pulse markdown now."
        )
        msg = model.invoke(
            [
                SystemMessage(content=prompt_path.read_text(encoding="utf-8")),
                HumanMessage(content=payload),
            ]
        )
        content = getattr(msg, "content", "") or ""
        if isinstance(content, list):
            content = "".join(
                block.get("text", "") if isinstance(block, dict) else str(block)
                for block in content
            )
        content = str(content).strip()
        if content and _word_count(content) >= 40:
            return content
    except Exception:
        return fallback_md
    return fallback_md


def _maybe_llm_shorten(cfg: AppConfig, markdown: str, max_words: int) -> str:
    model = get_generate_model(cfg)
    prompt_path = cfg.resolve(cfg.paths.prompts_dir) / "compose_shorten.txt"
    if model is None or not prompt_path.exists():
        return markdown
    try:
        from langchain_core.messages import HumanMessage, SystemMessage

        msg = model.invoke(
            [
                SystemMessage(
                    content=prompt_path.read_text(encoding="utf-8").format(max_words=max_words)
                ),
                HumanMessage(content=markdown),
            ]
        )
        content = getattr(msg, "content", "") or ""
        if isinstance(content, list):
            content = "".join(
                block.get("text", "") if isinstance(block, dict) else str(block)
                for block in content
            )
        content = str(content).strip()
        if content:
            return content
    except Exception:
        return markdown
    return markdown


def write_pulse(cfg: AppConfig, pulse: PulseResult) -> tuple[Path, Path]:
    md_path = cfg.resolve(cfg.paths.pulse_md)
    json_path = cfg.resolve(cfg.paths.pulse_json)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(pulse.markdown, encoding="utf-8")
    json_path.write_text(pulse.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return md_path, json_path
