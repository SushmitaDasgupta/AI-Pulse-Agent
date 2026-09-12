"""Unit tests for privacy scrubber."""

from __future__ import annotations

from src.config import load_config
from src.ingest.models import (
    CanonicalReview,
    DateWindow,
    NormalizedExport,
    Provenance,
)
from src.privacy.quality import looks_english, word_count
from src.privacy.scrub import REDACT, redact_text, scrub, scrub_review


def test_redact_email_phone_device_order():
    text = (
        "Contact alice@example.com or +1-555-123-4567. "
        "device_id: abcd-efgh-1234-5678 IMEI 490154203237518 order #ORD998877"
    )
    cleaned = redact_text(text)
    assert "alice@example.com" not in cleaned
    assert "+1-555-123-4567" not in cleaned
    assert "abcd-efgh-1234-5678" not in cleaned
    assert "490154203237518" not in cleaned
    assert "ORD998877" not in cleaned
    assert cleaned.count(REDACT) >= 4


def test_scrub_drops_empty_short_and_non_english():
    cfg = load_config()
    normalized = NormalizedExport(
        app_id=cfg.app_id,
        window=DateWindow(start="2026-07-02", end="2026-09-10"),
        provenance=Provenance(
            app_id=cfg.app_id,
            play_url=cfg.play_url,
            lang=cfg.lang,
            country=cfg.country,
            client="fixture",
            fetched_at="2026-09-10T00:00:00Z",
            mode="file",
        ),
        counts={"fetched": 5, "in_window": 5},
        reviews=[
            CanonicalReview(
                review_id="r_1",
                rating=2,
                title=None,
                text=(
                    "Crash on launch every time I open long chats. "
                    "Please email bob@example.com if you need logs."
                ),
                date="2026-08-01",
                locale="en_IN",
                source_app_id=cfg.app_id,
                week_bucket="2026-W31",
            ),
            CanonicalReview(
                review_id="r_2",
                rating=1,
                title=None,
                text="   ",
                date="2026-08-02",
                locale="en_IN",
                source_app_id=cfg.app_id,
                week_bucket="2026-W31",
            ),
            CanonicalReview(
                review_id="r_3",
                rating=3,
                title=None,
                text="Works fine offline for daily notes and chat.",
                date="2026-08-03",
                locale="en_IN",
                source_app_id=cfg.app_id,
                week_bucket="2026-W31",
            ),
            CanonicalReview(
                review_id="r_4",
                rating=5,
                title=None,
                text="nice app",
                date="2026-08-04",
                locale="en_IN",
                source_app_id=cfg.app_id,
                week_bucket="2026-W31",
            ),
            CanonicalReview(
                review_id="r_5",
                rating=1,
                title=None,
                text=(
                    "Aplicativo muito ruim. Nao entende o que o usuario esta falando "
                    "e muitas vezes nao consegue ajudar com coisas simples."
                ),
                date="2026-08-05",
                locale="en_IN",
                source_app_id=cfg.app_id,
                week_bucket="2026-W31",
            ),
        ],
    )
    cleaned = scrub(normalized)
    assert cleaned.counts["cleaned"] == 2
    assert cleaned.counts["dropped_empty"] == 1
    assert cleaned.counts["dropped_short"] == 1
    assert cleaned.counts["dropped_non_english"] == 1
    assert all(r.text.strip() for r in cleaned.reviews)
    assert all(word_count(r.text) >= 8 for r in cleaned.reviews)
    assert all(looks_english(r.text) for r in cleaned.reviews)
    assert all("userName" not in r.model_dump() for r in cleaned.reviews)
    joined = " ".join(r.text for r in cleaned.reviews)
    assert "bob@example.com" not in joined
    assert REDACT in joined


def test_scrub_review_none_on_empty():
    review = CanonicalReview(
        review_id="r_x",
        rating=1,
        text="   ",
        date="2026-08-01",
        source_app_id="com.openai.chatgpt",
        week_bucket="2026-W31",
    )
    assert scrub_review(review) is None


def test_scrub_review_none_on_short():
    review = CanonicalReview(
        review_id="r_short",
        rating=5,
        text="great app thanks",
        date="2026-08-01",
        source_app_id="com.openai.chatgpt",
        week_bucket="2026-W31",
    )
    assert scrub_review(review) is None


def test_looks_english_rejects_hindi_script_and_hinglish():
    assert looks_english(
        "This app is really helpful for students who need quick study help daily."
    )
    assert not looks_english(
        "थैंक यू थैंक यू बहुत अच्छे सपोर्ट कर रहे हैं और करते रहिएगा हम सब"
    )
    assert not looks_english(
        "sabhi kuchh theek thaak hai Magar kuchh jyada sawal jawab karne ke bad upgrade"
    )
