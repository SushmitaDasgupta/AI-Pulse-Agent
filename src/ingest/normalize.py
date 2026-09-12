"""Normalize raw Play export fields → canonical review schema + lookback window."""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from src.config import AppConfig
from src.ingest.models import (
    CanonicalReview,
    DateWindow,
    NormalizedExport,
    Provenance,
    RawExport,
)


def _as_utc_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).date()
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        if "T" in text:
            text = text.replace("Z", "+00:00")
            try:
                dt = datetime.fromisoformat(text)
            except ValueError:
                return None
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc).date()
        try:
            return date.fromisoformat(text[:10])
        except ValueError:
            return None
    return None


def opaque_review_id(source_id: str | None, text: str, date_str: str) -> str:
    """Hash-based id — never derive from username."""
    material = (source_id or "").strip() or f"{text}|{date_str}"
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]
    return f"r_{digest}"


def week_bucket_for(d: date) -> str:
    iso = d.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def lookback_window(cfg: AppConfig, as_of: date | None = None) -> DateWindow:
    end = as_of or datetime.now(timezone.utc).date()
    start = end - timedelta(weeks=cfg.lookback_weeks)
    return DateWindow(start=start.isoformat(), end=end.isoformat())


def _locale(cfg: AppConfig) -> str:
    return f"{cfg.lang}_{cfg.country.upper()}"


def map_raw_review(row: dict[str, Any], cfg: AppConfig) -> CanonicalReview | None:
    """Map google-play-scraper (or fixture) fields → canonical schema."""
    text = (row.get("content") or row.get("text") or "").strip()
    title_raw = row.get("title")
    title = (str(title_raw).strip() if title_raw else None) or None

    review_date = _as_utc_date(row.get("at") or row.get("date"))
    if review_date is None:
        return None

    rating_raw = row.get("score", row.get("rating", 0))
    try:
        rating = int(rating_raw)
    except (TypeError, ValueError):
        rating = 0

    date_str = review_date.isoformat()
    source_id = row.get("reviewId") or row.get("review_id")
    if source_id is not None:
        source_id = str(source_id)

    return CanonicalReview(
        review_id=opaque_review_id(source_id, text, date_str),
        rating=rating,
        title=title,
        text=text,
        date=date_str,
        locale=row.get("locale") or _locale(cfg),
        source_app_id=cfg.app_id,
        week_bucket=week_bucket_for(review_date),
    )


def normalize(
    raw: RawExport,
    cfg: AppConfig,
    *,
    as_of: date | None = None,
) -> NormalizedExport:
    window = lookback_window(cfg, as_of=as_of)
    start = date.fromisoformat(window.start)
    end = date.fromisoformat(window.end)

    mapped: list[CanonicalReview] = []
    in_window: list[CanonicalReview] = []
    skipped_undated = 0

    for row in raw.reviews:
        review = map_raw_review(row, cfg)
        if review is None:
            skipped_undated += 1
            continue
        mapped.append(review)
        d = date.fromisoformat(review.date)
        if start <= d <= end:
            in_window.append(review)

    provenance = raw.provenance.model_copy(
        update={
            "app_id": raw.provenance.app_id or cfg.app_id,
            "play_url": raw.provenance.play_url or cfg.play_url,
        }
    )
    return NormalizedExport(
        app_id=cfg.app_id,
        window=window,
        provenance=provenance,
        counts={
            "fetched": len(raw.reviews),
            "mapped": len(mapped),
            "in_window": len(in_window),
            "skipped_undated": skipped_undated,
        },
        reviews=in_window,
    )


def write_normalized(cfg: AppConfig, export: NormalizedExport, path: Path | None = None) -> Path:
    out = path or cfg.resolve(cfg.paths.normalized_reviews)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(export.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return out


def load_raw_export(path: Path) -> RawExport:
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if isinstance(payload, list):
        return RawExport(
            provenance=Provenance(
                app_id="unknown",
                play_url="",
                lang="",
                country="",
                client="file",
                fetched_at=datetime.now(timezone.utc).isoformat(),
                mode="file",
                source_path=str(path),
            ),
            reviews=payload,
        )
    return RawExport.model_validate(payload)


def load_normalized(path: Path) -> NormalizedExport:
    with path.open(encoding="utf-8") as handle:
        return NormalizedExport.model_validate(json.load(handle))
