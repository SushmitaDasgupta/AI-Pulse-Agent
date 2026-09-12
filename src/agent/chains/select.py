"""Select chain: Top 3 pain themes; Gemini generates quotes + actions."""

from __future__ import annotations

from pathlib import Path

from src.agent.catalog import CATALOG_BY_ID
from src.agent.chains.theme import assign_themes, load_themes, rank_pain_themes
from src.agent.corpus import load_cleaned, quote_candidates, word_count
from src.agent.llm import get_generate_model
from src.agent.schemas import (
    ActionRecord,
    QuoteRecord,
    SelectionResult,
    ThemesResult,
    TopThemeSummary,
)
from src.agent.validators import quote_is_substring
from src.config import AppConfig
from src.ingest.models import CanonicalReview


DEFAULT_ACTIONS: dict[str, tuple[str, str]] = {
    "t_paywall": (
        "Clarify free-tier limits before users hit the wall",
        "Reviews cite abrupt chat/photo caps and upgrade nags; surface remaining quota earlier.",
    ),
    "t_image": (
        "Make image/photo quotas understandable and fair",
        "Users complain about limited photo generation/upload; explain caps and improve fallback messaging.",
    ),
    "t_quality": (
        "Reduce confident-wrong answers and flip-flops",
        "1★ reviews describe incorrect answers that agree after correction; tighten grounding and correction UX.",
    ),
    "t_reliability": (
        "Stabilize crash/error paths after updates",
        "Complaints mention crashes, buggy updates, and hard failures — prioritize release soak and error clarity.",
    ),
    "t_login": (
        "Fix Google sign-in / reload loops on Android",
        "Account-access failures block usage entirely; triage device-validation and infinite-reload reports.",
    ),
}


def _snippet(text: str, max_words: int = 28) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text.strip()
    return " ".join(words[:max_words]).strip()


def _message_text(msg: object) -> str:
    content = getattr(msg, "content", "") or ""
    if isinstance(content, list):
        return "".join(
            block.get("text", "") if isinstance(block, dict) else str(block)
            for block in content
        )
    return str(content)


def pick_quotes_for_themes(
    top: list[TopThemeSummary],
    reviews: list[CanonicalReview],
    assignments: dict[str, str],
) -> list[QuoteRecord]:
    id_by_label = {cat.label: tid for tid, cat in CATALOG_BY_ID.items()}
    used_ids: set[str] = set()
    quotes: list[QuoteRecord] = []
    cleaned_texts = [r.text for r in reviews]

    for summary in top:
        theme_id = id_by_label.get(summary.label)
        if not theme_id:
            continue
        candidates = quote_candidates(
            reviews,
            theme_ids={theme_id},
            assignments=assignments,
            min_words=12,
            max_rating=3,
        )
        chosen: CanonicalReview | None = None
        for cand in candidates:
            if cand.review_id in used_ids:
                continue
            chosen = cand
            break
        if chosen is None:
            for review in sorted(reviews, key=lambda r: (r.rating, -word_count(r.text))):
                if assignments.get(review.review_id) != theme_id:
                    continue
                if word_count(review.text) < 8 or review.review_id in used_ids:
                    continue
                chosen = review
                break
        if chosen is None:
            continue
        text = _snippet(chosen.text)
        if not quote_is_substring(text, cleaned_texts):
            text = chosen.text.strip()
        used_ids.add(chosen.review_id)
        quotes.append(
            QuoteRecord(
                text=text,
                theme=summary.label,
                rating=chosen.rating,
                review_id=chosen.review_id,
            )
        )

    if len(quotes) < 3:
        for cand in quote_candidates(reviews, min_words=12, max_rating=3):
            if len(quotes) >= 3:
                break
            if cand.review_id in used_ids:
                continue
            theme_id = assignments.get(cand.review_id, "t_praise")
            label = (
                CATALOG_BY_ID[theme_id].label
                if theme_id in CATALOG_BY_ID
                else top[0].label
            )
            text = _snippet(cand.text)
            if not quote_is_substring(text, cleaned_texts):
                continue
            used_ids.add(cand.review_id)
            quotes.append(
                QuoteRecord(
                    text=text, theme=label, rating=cand.rating, review_id=cand.review_id
                )
            )

    return quotes[:3]


def build_actions(top: list[TopThemeSummary]) -> list[ActionRecord]:
    actions: list[ActionRecord] = []
    for summary in top:
        theme_id = next(
            (tid for tid, cat in CATALOG_BY_ID.items() if cat.label == summary.label),
            None,
        )
        if theme_id and theme_id in DEFAULT_ACTIONS:
            title, rationale = DEFAULT_ACTIONS[theme_id]
        else:
            title = f"Investigate {summary.label}"
            rationale = (
                f"Reviews cluster under {summary.label}; validate root cause with Support/Product."
            )
        actions.append(ActionRecord(title=title, rationale=rationale, theme=summary.label))
    while len(actions) < 3 and top:
        actions.append(
            ActionRecord(
                title="Monitor emerging review themes weekly",
                rationale="Keep the pulse cadence so new spikes are not missed.",
                theme=top[0].label,
            )
        )
    return actions[:3]


def run_select_chain(
    cfg: AppConfig,
    themes: ThemesResult | None = None,
) -> SelectionResult:
    export = load_cleaned(cfg)
    themes = themes or load_themes(cfg)
    assignments = assign_themes(export.reviews)
    ranked = rank_pain_themes(themes, assignments, export.reviews)[: cfg.pulse_top_themes]
    if not ranked:
        ranked = [t for t in themes.themes if t.theme_id != "t_praise"][: cfg.pulse_top_themes]

    top = [
        TopThemeSummary(
            label=t.label,
            summary=t.description,
            review_count=t.review_count,
        )
        for t in ranked
    ]

    # Deterministic candidates first (always available / offline fallback)
    fallback_quotes = pick_quotes_for_themes(top, export.reviews, assignments)
    fallback_actions = build_actions(top)
    selection = SelectionResult(
        top_themes=top, quotes=fallback_quotes, actions=fallback_actions
    )
    return _gemini_generate_quotes_and_actions(
        cfg, selection, export.reviews, assignments
    )


def _gemini_generate_quotes_and_actions(
    cfg: AppConfig,
    selection: SelectionResult,
    reviews: list[CanonicalReview],
    assignments: dict[str, str],
) -> SelectionResult:
    """Use Gemini to generate quotes + actions from validated candidate pools."""
    model = get_generate_model(cfg)
    if model is None:
        return selection

    prompt_path = cfg.resolve(cfg.paths.prompts_dir) / "select_generate.txt"
    legacy = cfg.resolve(cfg.paths.prompts_dir) / "select_actions.txt"
    system = (
        prompt_path.read_text(encoding="utf-8")
        if prompt_path.exists()
        else (
            legacy.read_text(encoding="utf-8")
            if legacy.exists()
            else "Return 3 quotes and 3 actions."
        )
    )

    # Candidate pool: complaint-heavy, theme-filtered where possible
    theme_ids = {
        tid
        for tid, cat in CATALOG_BY_ID.items()
        if cat.label in {t.label for t in selection.top_themes}
    }
    candidates = quote_candidates(
        reviews,
        theme_ids=theme_ids or None,
        assignments=assignments if theme_ids else None,
        min_words=12,
        max_rating=3,
    )[:40]
    if not candidates:
        candidates = quote_candidates(reviews, min_words=12, max_rating=3)[:40]

    cleaned_texts = [r.text for r in reviews]
    cand_blob = "\n".join(
        f"- id={c.review_id} theme={assignments.get(c.review_id)} "
        f"rating={c.rating} text={_snippet(c.text, 40)}"
        for c in candidates
    )
    themes_blob = "\n".join(
        f"- {t.label}: {t.summary} (n={t.review_count})" for t in selection.top_themes
    )

    try:
        from langchain_core.messages import HumanMessage, SystemMessage

        msg = model.invoke(
            [
                SystemMessage(content=system),
                HumanMessage(
                    content=(
                        f"Top themes:\n{themes_blob}\n\n"
                        f"Quote candidates (copy verbatim only):\n{cand_blob}\n"
                    )
                ),
            ]
        )
        content = _message_text(msg)
        quotes: list[QuoteRecord] = []
        actions: list[ActionRecord] = []
        by_id = {r.review_id: r for r in reviews}

        for line in content.splitlines():
            raw = line.strip()
            if not raw:
                continue
            upper = raw.upper()
            if upper.startswith("QUOTE"):
                parts = [p.strip() for p in raw.split("|")]
                if len(parts) < 3:
                    continue
                text, theme = parts[1], parts[2]
                # Prefer exact candidate match; else accept if substring of cleaned text
                matched = next(
                    (c for c in candidates if text in c.text or c.text.startswith(text)),
                    None,
                )
                if matched is None and not quote_is_substring(text, cleaned_texts):
                    # Try treating text as review_id
                    matched = by_id.get(text)
                    if matched:
                        text = _snippet(matched.text)
                if not quote_is_substring(text, cleaned_texts):
                    continue
                review_id = matched.review_id if matched else None
                rating = matched.rating if matched else None
                quotes.append(
                    QuoteRecord(text=text, theme=theme, rating=rating, review_id=review_id)
                )
            elif upper.startswith("ACTION"):
                parts = [p.strip() for p in raw.split("|")]
                if len(parts) < 4:
                    continue
                actions.append(
                    ActionRecord(
                        title=parts[1][:120],
                        rationale=parts[2][:240],
                        theme=parts[3][:80],
                    )
                )

        updates: dict[str, object] = {}
        if len(quotes) == 3:
            updates["quotes"] = quotes
        if len(actions) == 3:
            updates["actions"] = actions
        if updates:
            return selection.model_copy(update=updates)
    except Exception:
        return selection
    return selection


def write_selection(cfg: AppConfig, result: SelectionResult, path: Path | None = None) -> Path:
    out = path or cfg.resolve(cfg.paths.selection)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(result.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return out


def load_selection(cfg: AppConfig, path: Path | None = None) -> SelectionResult:
    out = path or cfg.resolve(cfg.paths.selection)
    return SelectionResult.model_validate_json(out.read_text(encoding="utf-8"))
