"""Acquire public ChatGPT Play listing reviews (live or saved file)."""

from __future__ import annotations

import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

from google_play_scraper import Sort, reviews as gps_reviews

from src.config import AppConfig
from src.ingest.models import Provenance, RawExport


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _timestamp_slug(dt: datetime | None = None) -> str:
    return (dt or _now_utc()).strftime("%Y%m%dT%H%M%SZ")


def _serialize_review(row: dict[str, Any]) -> dict[str, Any]:
    """Convert scraper row to JSON-safe dict (datetimes → ISO)."""
    out: dict[str, Any] = {}
    for key, value in row.items():
        if isinstance(value, datetime):
            out[key] = value.isoformat()
        else:
            out[key] = value
    return out


def _lookback_cutoff(cfg: AppConfig, as_of: datetime | None = None) -> datetime:
    end = as_of or _now_utc()
    return end - timedelta(weeks=cfg.lookback_weeks)


def _parse_review_at(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        text = value.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            return None
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    return None


def fetch_live_reviews(
    cfg: AppConfig,
    *,
    sleep_s: float = 0.4,
    reviews_fn: Callable[..., tuple[list[dict[str, Any]], Any]] | None = None,
    progress: Callable[[str], None] | None = None,
    empty_retries: int = 5,
    checkpoint_every: int = 5000,
    checkpoint_fn: Callable[[list[dict[str, Any]], int], None] | None = None,
) -> RawExport:
    """
    Paginate newest-first public reviews for cfg.app_id until lookback covered
    or max_reviews reached. No Google login / Play Console.
    """
    fetch = reviews_fn or gps_reviews
    sort = Sort.NEWEST
    page_size = min(200, max(1, cfg.acquire.max_reviews))
    cutoff = _lookback_cutoff(cfg)
    collected: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    token = None
    covered_past_cutoff = False
    page = 0
    consecutive_empty = 0
    last_checkpoint = 0
    log = progress or (lambda _msg: None)

    log(
        f"live fetch start app_id={cfg.app_id} lang={cfg.lang} country={cfg.country} "
        f"cutoff={cutoff.date()} max_reviews={cfg.acquire.max_reviews}"
    )

    while len(collected) < cfg.acquire.max_reviews and not covered_past_cutoff:
        count = min(page_size, cfg.acquire.max_reviews - len(collected))
        try:
            batch, token = fetch(
                cfg.app_id,
                lang=cfg.lang,
                country=cfg.country,
                sort=sort,
                count=count,
                continuation_token=token,
            )
        except Exception as exc:  # noqa: BLE001
            consecutive_empty += 1
            log(f"page fetch error ({exc}); retry {consecutive_empty}/{empty_retries}")
            if consecutive_empty >= empty_retries:
                break
            time.sleep(sleep_s * (2 ** consecutive_empty))
            continue

        page += 1
        if not batch:
            consecutive_empty += 1
            log(f"page={page} empty batch retry {consecutive_empty}/{empty_retries}")
            if consecutive_empty >= empty_retries:
                log("too many empty batches — stopping (rate limit or feed end)")
                break
            time.sleep(sleep_s * (2 ** consecutive_empty))
            continue

        consecutive_empty = 0
        oldest_in_batch: datetime | None = None
        for row in batch:
            rid = str(row.get("reviewId") or "")
            if rid and rid in seen_ids:
                continue
            if rid:
                seen_ids.add(rid)
            collected.append(_serialize_review(row))
            at = _parse_review_at(row.get("at"))
            if at is not None:
                if oldest_in_batch is None or at < oldest_in_batch:
                    oldest_in_batch = at
                if at < cutoff:
                    covered_past_cutoff = True

        if checkpoint_fn and len(collected) - last_checkpoint >= checkpoint_every:
            checkpoint_fn(collected, page)
            last_checkpoint = len(collected)

        if page == 1 or page % 10 == 0 or covered_past_cutoff or token is None:
            log(
                f"page={page} collected={len(collected)} "
                f"oldest_batch={oldest_in_batch} past_cutoff={covered_past_cutoff} "
                f"has_token={token is not None}"
            )

        if token is None:
            log(f"page={page} no continuation token — public feed exhausted")
            break
        if sleep_s > 0:
            time.sleep(sleep_s)

    fetched_at = _now_utc().isoformat()
    note = (
        "Public Play listing fetch via google-play-scraper; no Play Console. "
        f"Pages={page}; past_lookback_cutoff={covered_past_cutoff}; "
        f"cutoff={cutoff.date().isoformat()}."
    )
    if not covered_past_cutoff:
        note += (
            " Warning: stopped before fully covering lookback "
            "(max_reviews, rate limit, or feed exhaustion)."
        )

    return RawExport(
        provenance=Provenance(
            app_id=cfg.app_id,
            play_url=cfg.play_url,
            lang=cfg.lang,
            country=cfg.country,
            client=cfg.acquire.client,
            fetched_at=fetched_at,
            mode="live",
            note=note,
        ),
        reviews=collected,
    )


def _load_raw_json(path: Path) -> RawExport:
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if isinstance(payload, list):
        # Bare list fallback (legacy/simple dumps)
        return RawExport(
            provenance=Provenance(
                app_id="unknown",
                play_url="",
                lang="",
                country="",
                client="file",
                fetched_at=_now_utc().isoformat(),
                mode="file",
                source_path=str(path),
            ),
            reviews=payload,
        )
    if not isinstance(payload, dict):
        raise ValueError(f"Unexpected raw export shape: {path}")
    reviews = payload.get("reviews")
    if reviews is None and "result" in payload:
        reviews = payload["result"]
    provenance_raw = payload.get("provenance") or {}
    provenance = Provenance(
        app_id=provenance_raw.get("app_id") or "unknown",
        play_url=provenance_raw.get("play_url") or "",
        lang=provenance_raw.get("lang") or "",
        country=provenance_raw.get("country") or "",
        client=provenance_raw.get("client") or "file",
        fetched_at=provenance_raw.get("fetched_at") or _now_utc().isoformat(),
        mode="file",
        source_path=str(path),
        note=provenance_raw.get("note"),
    )
    return RawExport(provenance=provenance, reviews=list(reviews or []))


def _candidate_raw_paths(cfg: AppConfig) -> list[Path]:
    raw_dir = cfg.resolve(cfg.paths.raw_dir)
    paths = sorted(raw_dir.glob("play_reviews_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    # Prefer exports that match app_id when provenance is present
    matched: list[Path] = []
    unmatched: list[Path] = []
    for path in paths:
        try:
            export = _load_raw_json(path)
        except (OSError, json.JSONDecodeError, ValueError):
            continue
        if export.provenance.app_id in (cfg.app_id, "unknown"):
            if export.provenance.app_id == cfg.app_id:
                matched.append(path)
            else:
                unmatched.append(path)
    ordered = matched + unmatched
    fixture = cfg.fixture_path()
    if fixture.exists() and fixture not in ordered:
        ordered.append(fixture)
    return ordered


def load_file_export(cfg: AppConfig, path: Path | None = None) -> tuple[RawExport, Path]:
    """Load a prior public export for the same listing (file / offline mode)."""
    if path is not None:
        export = _load_raw_json(path)
        export.provenance.mode = "file"
        export.provenance.source_path = str(path)
        return export, path

    candidates = _candidate_raw_paths(cfg)
    if not candidates:
        raise FileNotFoundError(
            f"No raw exports found under {cfg.resolve(cfg.paths.raw_dir)} "
            f"(expected play_reviews_*.json or fixture {cfg.acquire.fixture_path})"
        )
    chosen = candidates[0]
    export = _load_raw_json(chosen)
    export.provenance.mode = "file"
    export.provenance.source_path = str(chosen)
    if export.provenance.app_id == "unknown":
        export.provenance.app_id = cfg.app_id
    if not export.provenance.play_url:
        export.provenance.play_url = cfg.play_url
    if not export.provenance.lang:
        export.provenance.lang = cfg.lang
    if not export.provenance.country:
        export.provenance.country = cfg.country
    return export, chosen


def write_raw_export(cfg: AppConfig, export: RawExport, path: Path | None = None) -> Path:
    raw_dir = cfg.resolve(cfg.paths.raw_dir)
    raw_dir.mkdir(parents=True, exist_ok=True)
    out = path or (raw_dir / f"play_reviews_{_timestamp_slug()}.json")
    payload = {
        "provenance": export.provenance.model_dump(),
        "reviews": export.reviews,
    }
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return out


def acquire(
    cfg: AppConfig,
    *,
    retries: int = 3,
    backoff_s: float = 1.0,
    reviews_fn: Callable[..., tuple[list[dict[str, Any]], Any]] | None = None,
) -> tuple[RawExport, Path]:
    """
    Acquire raw reviews.

    - mode=live: fetch public listing; on failure after retries, fall back to latest file.
    - mode=file: load latest matching data/raw export (or fixture).
    """
    mode = cfg.acquire.mode
    if mode == "file":
        return load_file_export(cfg)

    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            export = fetch_live_reviews(cfg, reviews_fn=reviews_fn)
            path = write_raw_export(cfg, export)
            return export, path
        except Exception as exc:  # noqa: BLE001 — retry then fall back
            last_error = exc
            if attempt < retries:
                time.sleep(backoff_s * attempt)

    # Fall back to last good file export
    try:
        export, source = load_file_export(cfg)
        export.provenance.note = (
            f"Live fetch failed ({last_error}); fell back to saved export {source}"
        )
        return export, source
    except FileNotFoundError as exc:
        raise RuntimeError(
            f"Live acquire failed after {retries} attempts ({last_error}) "
            "and no saved data/raw export was available"
        ) from exc
