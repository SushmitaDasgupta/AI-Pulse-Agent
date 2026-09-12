"""Deterministic validators for pulse artifacts (P2 hard gates)."""

from __future__ import annotations

from src.agent.schemas import PulseResult, SelectionResult, ThemesResult


def validate_themes(themes: ThemesResult, max_themes: int = 5) -> list[str]:
    errors: list[str] = []
    if not themes.themes:
        errors.append("themes list is empty")
    if len(themes.themes) > max_themes:
        errors.append(f"theme count {len(themes.themes)} exceeds max {max_themes}")
    ids = [t.theme_id for t in themes.themes]
    if len(ids) != len(set(ids)):
        errors.append("duplicate theme_id values")
    return errors


def validate_selection(
    selection: SelectionResult,
    *,
    cleaned_texts: list[str] | None = None,
    require_populated: bool = True,
) -> list[str]:
    errors: list[str] = []
    if require_populated:
        if len(selection.top_themes) < 1:
            errors.append("expected at least 1 top theme")
        if len(selection.top_themes) > 3:
            errors.append("expected at most Top 3 themes")
        if len(selection.quotes) != 3:
            errors.append("expected exactly 3 quotes")
        if len(selection.actions) != 3:
            errors.append("expected exactly 3 actions")
    else:
        if selection.quotes and len(selection.quotes) != 3:
            errors.append("expected exactly 3 quotes")
        if selection.actions and len(selection.actions) != 3:
            errors.append("expected exactly 3 actions")
        if selection.top_themes and len(selection.top_themes) > 3:
            errors.append("expected at most Top 3 themes")

    theme_labels = {t.label for t in selection.top_themes}
    for action in selection.actions:
        if theme_labels and action.theme not in theme_labels:
            # Allow actions mapped to any known top theme label string from selection quotes too
            quote_themes = {q.theme for q in selection.quotes}
            if action.theme not in theme_labels and action.theme not in quote_themes:
                errors.append(f"action theme not in top themes: {action.theme}")

    if cleaned_texts is not None:
        for quote in selection.quotes:
            if not quote_is_substring(quote.text, cleaned_texts):
                errors.append(f"quote is not a cleaned-text substring: {quote.text[:80]!r}")
    return errors


def validate_pulse(pulse: PulseResult, max_words: int = 250) -> list[str]:
    errors: list[str] = []
    words = len(pulse.markdown.split()) if pulse.markdown else pulse.word_count
    if words > max_words:
        errors.append(f"word_count {words} exceeds max {max_words}")
    if pulse.word_count and pulse.markdown and pulse.word_count != len(pulse.markdown.split()):
        # Soft inconsistency — recompute gate uses markdown
        pass
    if not pulse.markdown.strip():
        errors.append("pulse markdown is empty")
    lower = pulse.markdown.lower()
    if "cleaned reviews" not in lower and "reviews:" not in lower:
        errors.append("pulse header should state cleaned review count")
    return errors


def quote_is_substring(quote: str, cleaned_texts: list[str]) -> bool:
    """True if quote appears verbatim in some cleaned review text (P2 gate)."""
    q = quote.strip()
    if not q:
        return False
    return any(q in text for text in cleaned_texts)


def validate_pulse_artifacts(
    themes: ThemesResult,
    selection: SelectionResult,
    pulse: PulseResult,
    *,
    cleaned_texts: list[str],
    max_themes: int = 5,
    max_words: int = 250,
) -> list[str]:
    """Run all hard gates; empty list means pass."""
    errors: list[str] = []
    errors.extend(validate_themes(themes, max_themes=max_themes))
    errors.extend(
        validate_selection(selection, cleaned_texts=cleaned_texts, require_populated=True)
    )
    errors.extend(validate_pulse(pulse, max_words=max_words))
    return errors
