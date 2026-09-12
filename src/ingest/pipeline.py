"""Ingest orchestration: acquire → normalize → scrub."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Callable

from src.config import AppConfig
from src.ingest.acquire import acquire as acquire_reviews
from src.ingest.models import CleanedExport, NormalizedExport, RawExport
from src.ingest.normalize import load_normalized, load_raw_export, normalize, write_normalized
from src.privacy.scrub import scrub, write_cleaned


@dataclass
class IngestResult:
    raw_path: Path | None = None
    normalized_path: Path | None = None
    cleaned_path: Path | None = None
    raw: RawExport | None = None
    normalized: NormalizedExport | None = None
    cleaned: CleanedExport | None = None
    messages: list[str] | None = None

    def __post_init__(self) -> None:
        if self.messages is None:
            self.messages = []


def run_acquire(
    cfg: AppConfig,
    *,
    reviews_fn: Callable[..., tuple[list[dict[str, Any]], Any]] | None = None,
) -> IngestResult:
    export, path = acquire_reviews(cfg, reviews_fn=reviews_fn)
    msg = (
        f"acquire: mode={export.provenance.mode} path={path} "
        f"fetched={len(export.reviews)} app_id={export.provenance.app_id} "
        f"url={export.provenance.play_url}"
    )
    return IngestResult(raw_path=path, raw=export, messages=[msg])


def run_normalize(
    cfg: AppConfig,
    *,
    raw_path: Path | None = None,
    raw: RawExport | None = None,
    as_of: date | None = None,
) -> IngestResult:
    if raw is None:
        if raw_path is None:
            # Prefer latest non-fixture timestamped export if present
            from src.ingest.acquire import load_file_export

            raw, raw_path = load_file_export(cfg)
        else:
            raw = load_raw_export(raw_path)

    normalized = normalize(raw, cfg, as_of=as_of)
    out = write_normalized(cfg, normalized)
    counts = normalized.counts
    msg = (
        f"normalize: fetched={counts.get('fetched', 0)} → "
        f"in_window={counts.get('in_window', 0)} "
        f"window={normalized.window.start}..{normalized.window.end} → {out}"
    )
    return IngestResult(
        raw_path=raw_path,
        raw=raw,
        normalized_path=out,
        normalized=normalized,
        messages=[msg],
    )


def run_scrub(
    cfg: AppConfig,
    *,
    normalized_path: Path | None = None,
    normalized: NormalizedExport | None = None,
) -> IngestResult:
    if normalized is None:
        path = normalized_path or cfg.resolve(cfg.paths.normalized_reviews)
        if not path.exists():
            raise FileNotFoundError(f"Normalized reviews not found: {path}")
        normalized = load_normalized(path)
        normalized_path = path

    cleaned = scrub(normalized)
    out = write_cleaned(cfg, cleaned)
    counts = cleaned.counts
    msg = (
        f"scrub: in_window={counts.get('in_window', len(normalized.reviews))} → "
        f"cleaned={counts.get('cleaned', 0)} "
        f"dropped_empty={counts.get('dropped_empty', 0)} "
        f"dropped_short={counts.get('dropped_short', 0)} "
        f"dropped_non_english={counts.get('dropped_non_english', 0)} → {out}"
    )
    return IngestResult(
        normalized_path=normalized_path,
        normalized=normalized,
        cleaned_path=out,
        cleaned=cleaned,
        messages=[msg],
    )


def run_ingest(
    cfg: AppConfig,
    *,
    reviews_fn: Callable[..., tuple[list[dict[str, Any]], Any]] | None = None,
    as_of: date | None = None,
) -> IngestResult:
    """Full acquire → normalize → scrub bundle."""
    acquired = run_acquire(cfg, reviews_fn=reviews_fn)
    normalized = run_normalize(
        cfg, raw_path=acquired.raw_path, raw=acquired.raw, as_of=as_of
    )
    cleaned = run_scrub(cfg, normalized_path=normalized.normalized_path, normalized=normalized.normalized)
    messages = (acquired.messages or []) + (normalized.messages or []) + (cleaned.messages or [])
    return IngestResult(
        raw_path=acquired.raw_path,
        normalized_path=normalized.normalized_path,
        cleaned_path=cleaned.cleaned_path,
        raw=acquired.raw,
        normalized=normalized.normalized,
        cleaned=cleaned.cleaned,
        messages=messages,
    )
