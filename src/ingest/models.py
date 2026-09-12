"""Canonical review models for ingest / privacy stages."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class DateWindow(BaseModel):
    start: str
    end: str


class Provenance(BaseModel):
    app_id: str
    play_url: str
    lang: str
    country: str
    client: str
    fetched_at: str
    mode: str = "file"
    source_path: Optional[str] = None
    note: Optional[str] = None


class RawExport(BaseModel):
    provenance: Provenance
    reviews: list[dict[str, Any]] = Field(default_factory=list)


class CanonicalReview(BaseModel):
    review_id: str
    rating: int
    title: Optional[str] = None
    text: str
    date: str
    locale: Optional[str] = None
    source_app_id: str
    week_bucket: str


class NormalizedExport(BaseModel):
    app_id: str
    window: DateWindow
    provenance: Provenance
    counts: dict[str, int] = Field(default_factory=dict)
    reviews: list[CanonicalReview] = Field(default_factory=list)


class CleanedExport(BaseModel):
    app_id: str
    window: DateWindow
    provenance: Provenance
    counts: dict[str, int] = Field(default_factory=dict)
    reviews: list[CanonicalReview] = Field(default_factory=list)
