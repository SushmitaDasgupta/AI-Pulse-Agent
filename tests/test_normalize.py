"""Unit tests for normalize + lookback windowing."""

from __future__ import annotations

from datetime import date

from src.config import load_config
from src.ingest.models import Provenance, RawExport
from src.ingest.normalize import map_raw_review, normalize, opaque_review_id


def test_map_raw_review_field_mapping():
    cfg = load_config()
    row = {
        "reviewId": "abc-123",
        "userName": "ShouldNeverBecomeId",
        "content": "Streaming stalls mid-answer.",
        "score": 3,
        "at": "2026-08-20T14:30:00.000Z",
        "title": None,
    }
    review = map_raw_review(row, cfg)
    assert review is not None
    assert review.rating == 3
    assert review.text == "Streaming stalls mid-answer."
    assert review.date == "2026-08-20"
    assert review.source_app_id == "com.openai.chatgpt"
    assert review.locale == "en_IN"
    assert review.week_bucket.startswith("2026-W")
    assert review.review_id.startswith("r_")
    assert "ShouldNeverBecomeId" not in review.review_id
    assert review.review_id == opaque_review_id("abc-123", review.text, review.date)


def test_normalize_lookback_and_counts():
    cfg = load_config()
    raw = RawExport(
        provenance=Provenance(
            app_id=cfg.app_id,
            play_url=cfg.play_url,
            lang=cfg.lang,
            country=cfg.country,
            client="fixture",
            fetched_at="2026-09-10T00:00:00Z",
            mode="file",
        ),
        reviews=[
            {
                "reviewId": "in",
                "userName": "A",
                "content": "Inside window",
                "score": 2,
                "at": "2026-08-01T00:00:00Z",
            },
            {
                "reviewId": "out",
                "userName": "B",
                "content": "Outside window",
                "score": 5,
                "at": "2026-01-01T00:00:00Z",
            },
            {
                "reviewId": "empty",
                "userName": "C",
                "content": "  ",
                "score": 1,
                "at": "2026-08-02T00:00:00Z",
            },
        ],
    )
    result = normalize(raw, cfg, as_of=date(2026, 9, 10))
    assert result.window.start == "2026-07-16"  # 8 weeks before 2026-09-10
    assert result.window.end == "2026-09-10"
    assert result.counts["fetched"] == 3
    assert result.counts["in_window"] == 2  # in + empty (empty dropped later by scrub)
    assert all(r.date >= result.window.start for r in result.reviews)
    assert all("userName" not in r.model_dump() for r in result.reviews)
    texts = {r.text for r in result.reviews}
    assert "Outside window" not in texts
    assert "Inside window" in texts


def test_opaque_id_ignores_username():
    a = opaque_review_id("src1", "hello", "2026-08-01")
    b = opaque_review_id("src1", "hello", "2026-08-01")
    assert a == b
    assert a.startswith("r_")
