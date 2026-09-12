"""Phase-2 theme / select / compose / validate tests (offline, no LLM)."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.agent.catalog import classify_review
from src.agent.chains.compose import run_compose_chain, write_pulse
from src.agent.chains.select import run_select_chain, write_selection
from src.agent.chains.theme import run_theme_chain, write_themes
from src.agent.corpus import load_cleaned, stratified_sample
from src.agent.validators import quote_is_substring, validate_pulse_artifacts
from src.config import load_config
from src.ingest.models import (
    CanonicalReview,
    CleanedExport,
    DateWindow,
    Provenance,
)


def _tiny_cleaned(tmp_path: Path) -> Path:
    reviews = [
        CanonicalReview(
            review_id="r1",
            rating=1,
            text=(
                "I can't login or sign in with my Google account and it keeps reload forever "
                "so I never get into the app at all."
            ),
            date="2026-09-01",
            source_app_id="com.openai.chatgpt",
            week_bucket="2026-W36",
        ),
        CanonicalReview(
            review_id="r2",
            rating=2,
            text=(
                "Free limit is reached after a few texts and it forces me to upgrade to Plus "
                "before I can chat again which is frustrating."
            ),
            date="2026-09-02",
            source_app_id="com.openai.chatgpt",
            week_bucket="2026-W36",
        ),
        CanonicalReview(
            review_id="r3",
            rating=1,
            text=(
                "Image generation is limited and I can't upload photos after a few messages "
                "even though I need pictures for homework help."
            ),
            date="2026-09-03",
            source_app_id="com.openai.chatgpt",
            week_bucket="2026-W36",
        ),
        CanonicalReview(
            review_id="r4",
            rating=2,
            text=(
                "It gives wrong answers and when I say that is incorrect it also says yes I "
                "misunderstood and then changes again."
            ),
            date="2026-09-04",
            source_app_id="com.openai.chatgpt",
            week_bucket="2026-W36",
        ),
        CanonicalReview(
            review_id="r5",
            rating=5,
            text=(
                "Amazing and very helpful app for studies I love using ChatGPT every day for "
                "homework and it is the best app."
            ),
            date="2026-09-05",
            source_app_id="com.openai.chatgpt",
            week_bucket="2026-W36",
        ),
        CanonicalReview(
            review_id="r6",
            rating=1,
            text=(
                "The app keeps crashing after the latest update and shows random errors that "
                "make it unusable on my phone."
            ),
            date="2026-09-06",
            source_app_id="com.openai.chatgpt",
            week_bucket="2026-W36",
        ),
    ]
    export = CleanedExport(
        app_id="com.openai.chatgpt",
        window=DateWindow(start="2026-07-16", end="2026-09-10"),
        provenance=Provenance(
            app_id="com.openai.chatgpt",
            play_url="https://play.google.com/store/apps/details?id=com.openai.chatgpt&hl=en_IN",
            lang="en",
            country="in",
            client="test",
            fetched_at="2026-09-10T00:00:00Z",
            mode="file",
        ),
        counts={"cleaned": len(reviews)},
        reviews=reviews,
    )
    path = tmp_path / "reviews.cleaned.json"
    path.write_text(export.model_dump_json(indent=2), encoding="utf-8")
    return path


def test_classify_review_pain_over_praise():
    assert classify_review("I can't login with my Google account reload forever please fix") == "t_login"
    assert classify_review("upgrade to plus because free limit reached after chats") == "t_paywall"
    assert classify_review("amazing best app very helpful for studies love it a lot") == "t_praise"


def test_pulse_pipeline_offline(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    cleaned = _tiny_cleaned(tmp_path)
    cfg = load_config()
    monkeypatch.setattr(cfg.paths, "cleaned_reviews", str(cleaned))
    monkeypatch.setattr(cfg.paths, "themes", str(tmp_path / "themes.json"))
    monkeypatch.setattr(cfg.paths, "selection", str(tmp_path / "selection.json"))
    monkeypatch.setattr(cfg.paths, "pulse_md", str(tmp_path / "pulse.md"))
    monkeypatch.setattr(cfg.paths, "pulse_json", str(tmp_path / "pulse.json"))
    monkeypatch.setattr(cfg.paths, "processed_dir", str(tmp_path))
    monkeypatch.setattr(cfg.paths, "out_dir", str(tmp_path))

    themes, assignments, stats = run_theme_chain(cfg, sample_size=10)
    assert stats.n == 6
    assert 1 <= len(themes.themes) <= 5
    assert any(t.theme_id != "t_praise" for t in themes.themes)
    write_themes(cfg, themes)

    selection = run_select_chain(cfg, themes=themes)
    assert len(selection.top_themes) <= 3
    assert len(selection.quotes) == 3
    assert len(selection.actions) == 3
    write_selection(cfg, selection)

    export = load_cleaned(cfg)
    texts = [r.text for r in export.reviews]
    for quote in selection.quotes:
        assert quote_is_substring(quote.text, texts)

    pulse = run_compose_chain(cfg, selection=selection, themes=themes)
    write_pulse(cfg, pulse)
    assert pulse.word_count <= cfg.max_pulse_words
    assert "Cleaned reviews" in pulse.markdown or "cleaned reviews" in pulse.markdown.lower()

    errors = validate_pulse_artifacts(
        themes,
        selection,
        pulse,
        cleaned_texts=texts,
        max_themes=cfg.max_themes,
        max_words=cfg.max_pulse_words,
    )
    assert errors == []
    assert assignments


def test_quote_substring_gate():
    texts = ["hello world from a cleaned review body"]
    assert quote_is_substring("hello world", texts)
    assert not quote_is_substring("goodbye moon", texts)


def test_stratified_sample_prefers_low_ratings():
    reviews = [
        CanonicalReview(
            review_id=f"r{i}",
            rating=5 if i < 20 else 1,
            text=" ".join(["word"] * (10 + i)),
            date="2026-09-01",
            source_app_id="com.openai.chatgpt",
            week_bucket="2026-W36",
        )
        for i in range(40)
    ]
    sample = stratified_sample(reviews, size=10, seed=0)
    assert len(sample) == 10
    assert sum(1 for r in sample if r.rating <= 3) >= 4
