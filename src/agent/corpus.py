"""Load Phase-1 cleaned reviews and build stratified samples for P2."""

from __future__ import annotations

import json
import random
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from src.config import AppConfig
from src.ingest.models import CanonicalReview, CleanedExport


@dataclass
class CorpusStats:
    n: int
    date_min: str | None
    date_max: str | None
    rating_hist: dict[int, int]
    week_hist: dict[str, int]
    lookback_start: str | None
    lookback_end: str | None
    undercovered: bool

    def log_line(self) -> str:
        hist = ",".join(f"{k}:{v}" for k, v in sorted(self.rating_hist.items()))
        return (
            f"corpus n={self.n} dates={self.date_min}..{self.date_max} "
            f"ratings={hist} undercovered={self.undercovered} "
            f"lookback={self.lookback_start}..{self.lookback_end}"
        )


def load_cleaned(cfg: AppConfig, path: Path | None = None) -> CleanedExport:
    """Load canonical cleaned export (JSON primary)."""
    out = path or cfg.resolve(cfg.paths.cleaned_reviews)
    if not out.exists():
        raise FileNotFoundError(f"Cleaned reviews not found: {out}")
    payload = json.loads(out.read_text(encoding="utf-8"))
    return CleanedExport.model_validate(payload)


def corpus_stats(export: CleanedExport) -> CorpusStats:
    reviews = export.reviews
    dates = [r.date for r in reviews if r.date]
    ratings = Counter(r.rating for r in reviews)
    weeks = Counter(r.week_bucket for r in reviews if r.week_bucket)
    date_min = min(dates) if dates else None
    date_max = max(dates) if dates else None
    lookback_start = export.window.start if export.window else None
    lookback_end = export.window.end if export.window else None
    undercovered = False
    if date_min and lookback_start and date_min > lookback_start:
        undercovered = True
    return CorpusStats(
        n=len(reviews),
        date_min=date_min,
        date_max=date_max,
        rating_hist=dict(sorted(ratings.items())),
        week_hist=dict(sorted(weeks.items())),
        lookback_start=lookback_start,
        lookback_end=lookback_end,
        undercovered=undercovered,
    )


def word_count(text: str) -> int:
    return len(text.split())


def stratified_sample(
    reviews: list[CanonicalReview],
    *,
    size: int = 1200,
    seed: int = 42,
) -> list[CanonicalReview]:
    """
    Oversample 1–3★ and longer reviews for theme discovery / LLM batches.

    Targets roughly: 50% low (1–3), 20% mid-ish 4★, 30% 5★, preferring longer bodies.
    """
    if size <= 0 or not reviews:
        return []
    if len(reviews) <= size:
        return list(reviews)

    rng = random.Random(seed)

    def scored(pool: list[CanonicalReview]) -> list[CanonicalReview]:
        # Prefer longer text when sampling within a rating band.
        return sorted(pool, key=lambda r: (word_count(r.text), r.rating), reverse=True)

    low = scored([r for r in reviews if r.rating <= 3])
    four = scored([r for r in reviews if r.rating == 4])
    five = scored([r for r in reviews if r.rating == 5])

    n_low = min(len(low), int(size * 0.50))
    n_four = min(len(four), int(size * 0.20))
    n_five = min(len(five), size - n_low - n_four)

    picked: list[CanonicalReview] = []
    picked.extend(_take_spread(low, n_low, rng))
    picked.extend(_take_spread(four, n_four, rng))
    picked.extend(_take_spread(five, n_five, rng))

    if len(picked) < size:
        remaining = [r for r in reviews if r not in picked]
        rng.shuffle(remaining)
        picked.extend(remaining[: size - len(picked)])

    rng.shuffle(picked)
    return picked[:size]


def _take_spread(
    ordered: list[CanonicalReview], n: int, rng: random.Random
) -> list[CanonicalReview]:
    if n <= 0 or not ordered:
        return []
    if len(ordered) <= n:
        return list(ordered)
    # Take top half by length, plus random from the rest for diversity.
    top = ordered[: max(n // 2, 1)]
    rest = ordered[len(top) :]
    rng.shuffle(rest)
    return (top + rest)[:n]


def quote_candidates(
    reviews: list[CanonicalReview],
    *,
    theme_ids: set[str] | None = None,
    assignments: dict[str, str] | None = None,
    min_words: int = 12,
    max_rating: int = 3,
) -> list[CanonicalReview]:
    """Complaint-heavy, coherent candidates for verbatim quotes."""
    out: list[CanonicalReview] = []
    for review in reviews:
        if review.rating > max_rating:
            continue
        if word_count(review.text) < min_words:
            continue
        if not _looks_quotable(review.text):
            continue
        if theme_ids and assignments is not None:
            tid = assignments.get(review.review_id)
            if tid not in theme_ids:
                continue
        out.append(review)
    out.sort(key=lambda r: (r.rating, -word_count(r.text)))
    return out


def _looks_quotable(text: str) -> bool:
    letters = sum(1 for ch in text if ch.isalpha())
    if letters < 20:
        return False
    # Heavy emoji / clutter
    non_space = max(len(text) - text.count(" "), 1)
    weird = sum(1 for ch in text if ord(ch) > 0x2FFF)
    if weird / non_space > 0.25:
        return False
    return True
