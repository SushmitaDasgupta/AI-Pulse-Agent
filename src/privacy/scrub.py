"""Deterministic PII scrub before any LLM / delivery stage."""

from __future__ import annotations

import csv
import re
from pathlib import Path

from src.config import AppConfig
from src.ingest.models import CanonicalReview, CleanedExport, NormalizedExport
from src.privacy.quality import MIN_WORDS, looks_english, word_count

# Contact / identity patterns in free text
EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE_RE = re.compile(
    r"(?<!\w)(?:\+?\d{1,3}[\s-]?)?(?:\(?\d{2,4}\)?[\s-]?)?\d{3,4}[\s-]?\d{4}(?!\w)"
)
# Common device / order-like IDs (IMEI-ish, long hex, order tokens)
DEVICE_ID_RE = re.compile(
    r"\b(?:IMEI[:\s-]*)?\d{15}\b|\b(?:device|android)[_ -]?id[:\s-]*[A-Za-z0-9-]{8,}\b",
    re.IGNORECASE,
)
ORDER_ID_RE = re.compile(r"\b(?:order|txn|transaction)[#:\s-]*[A-Za-z0-9-]{6,}\b", re.IGNORECASE)

REDACT = "[redacted]"

CSV_FIELDS = (
    "review_id",
    "rating",
    "title",
    "text",
    "date",
    "locale",
    "source_app_id",
    "week_bucket",
)


def redact_text(text: str) -> str:
    """Redact PII-like tokens; leave remaining wording unchanged for quote fidelity."""
    cleaned = EMAIL_RE.sub(REDACT, text)
    cleaned = DEVICE_ID_RE.sub(REDACT, cleaned)
    cleaned = ORDER_ID_RE.sub(REDACT, cleaned)
    cleaned = PHONE_RE.sub(REDACT, cleaned)
    return cleaned


def scrub_review(review: CanonicalReview) -> CanonicalReview | None:
    """
    Drop identity fields (already absent on canonical model), redact body/title,
    drop empty / too-short / non-English text.
    """
    text = redact_text(review.text).strip()
    title = redact_text(review.title).strip() if review.title else None
    if title == "":
        title = None
    if not text:
        return None
    if word_count(text) < MIN_WORDS:
        return None
    if not looks_english(text):
        return None
    return review.model_copy(update={"text": text, "title": title})


def scrub(normalized: NormalizedExport) -> CleanedExport:
    cleaned: list[CanonicalReview] = []
    dropped_empty = 0
    dropped_short = 0
    dropped_non_english = 0
    for review in normalized.reviews:
        text = redact_text(review.text).strip()
        title = redact_text(review.title).strip() if review.title else None
        if title == "":
            title = None
        if not text:
            dropped_empty += 1
            continue
        if word_count(text) < MIN_WORDS:
            dropped_short += 1
            continue
        if not looks_english(text):
            dropped_non_english += 1
            continue
        cleaned.append(review.model_copy(update={"text": text, "title": title}))

    counts = dict(normalized.counts)
    counts["cleaned"] = len(cleaned)
    counts["dropped_empty"] = dropped_empty
    counts["dropped_short"] = dropped_short
    counts["dropped_non_english"] = dropped_non_english

    return CleanedExport(
        app_id=normalized.app_id,
        window=normalized.window,
        provenance=normalized.provenance,
        counts=counts,
        reviews=cleaned,
    )


def write_cleaned_csv(export: CleanedExport, path: Path) -> Path:
    """Write cleaned reviews as CSV for Phase-1 inspection / downstream tools."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for review in export.reviews:
            row = review.model_dump()
            writer.writerow({key: row.get(key) for key in CSV_FIELDS})
    return path


def write_cleaned(cfg: AppConfig, export: CleanedExport, path: Path | None = None) -> Path:
    out = path or cfg.resolve(cfg.paths.cleaned_reviews)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(export.model_dump_json(indent=2) + "\n", encoding="utf-8")
    csv_path = cfg.resolve(cfg.paths.cleaned_reviews_csv)
    write_cleaned_csv(export, csv_path)
    return out
