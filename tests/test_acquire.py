"""Acquire file-mode + optional live smoke tests."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.config import load_config
from src.ingest.acquire import acquire, fetch_live_reviews, load_file_export, write_raw_export
from src.ingest.pipeline import run_ingest


def test_file_mode_loads_fixture():
    cfg = load_config()
    assert cfg.acquire.mode == "file"
    export, path = acquire(cfg)
    assert path.exists()
    assert export.provenance.app_id == "com.openai.chatgpt"
    assert len(export.reviews) >= 6
    assert all("userName" in row for row in export.reviews)  # raw still has identity fields


def test_run_ingest_file_mode_writes_cleaned(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    cfg = load_config()
    # Redirect artifact writes into tmp
    monkeypatch.setattr(cfg.paths, "normalized_reviews", str(tmp_path / "normalized.json"))
    monkeypatch.setattr(cfg.paths, "cleaned_reviews", str(tmp_path / "cleaned.json"))
    monkeypatch.setattr(cfg.paths, "interim_dir", str(tmp_path))
    monkeypatch.setattr(cfg.paths, "processed_dir", str(tmp_path))

    result = run_ingest(cfg, as_of=__import__("datetime").date(2026, 9, 10))
    assert result.cleaned_path and result.cleaned_path.exists()
    assert result.normalized_path and result.normalized_path.exists()
    assert result.cleaned is not None
    assert result.cleaned.counts["fetched"] == 8
    assert result.cleaned.counts["in_window"] == 7  # excludes Jan 2026
    assert result.cleaned.counts["cleaned"] == 6  # drops empty body
    assert result.cleaned.window.start <= min(r.date for r in result.cleaned.reviews)
    payload = result.cleaned.model_dump()
    blob = str(payload)
    assert "userName" not in blob
    assert "alice@example.com" not in blob
    assert "+1-555-123-4567" not in blob
    assert all(r["text"].strip() for r in payload["reviews"])


def test_load_file_export_prefers_matching_app(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    cfg = load_config()
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    monkeypatch.setattr(cfg.paths, "raw_dir", str(raw_dir))
    monkeypatch.setattr(cfg.acquire, "fixture_path", str(tmp_path / "missing.json"))

    from src.ingest.models import Provenance, RawExport

    export = RawExport(
        provenance=Provenance(
            app_id=cfg.app_id,
            play_url=cfg.play_url,
            lang=cfg.lang,
            country=cfg.country,
            client="test",
            fetched_at=datetime.now(timezone.utc).isoformat(),
            mode="file",
        ),
        reviews=[{"reviewId": "x", "content": "hi", "score": 5, "at": "2026-08-01T00:00:00Z"}],
    )
    written = write_raw_export(cfg, export, path=raw_dir / "play_reviews_test.json")
    loaded, path = load_file_export(cfg)
    assert path == written
    assert len(loaded.reviews) == 1


@pytest.mark.network
def test_live_acquire_smoke_chatgpt_listing():
    """Live public listing smoke — skip unless PULSATOR_LIVE=1."""
    if os.environ.get("PULSATOR_LIVE") != "1":
        pytest.skip("Set PULSATOR_LIVE=1 to run live Play listing smoke test")
    cfg = load_config()
    cfg.acquire.max_reviews = 40
    export = fetch_live_reviews(cfg, sleep_s=0.2)
    assert export.provenance.app_id == "com.openai.chatgpt"
    assert export.provenance.lang == "en"
    assert export.provenance.country == "in"
    assert len(export.reviews) > 0
    assert "content" in export.reviews[0] or "score" in export.reviews[0]
