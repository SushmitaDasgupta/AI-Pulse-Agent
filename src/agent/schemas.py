"""Pydantic contracts for themes / selection / pulse artifacts."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class DateWindow(BaseModel):
    start: str
    end: str


class ThemeRecord(BaseModel):
    theme_id: str
    label: str
    description: str = ""
    review_count: int = 0
    share: float = 0.0
    avg_rating: Optional[float] = None
    example_ids: list[str] = Field(default_factory=list)


class ThemesResult(BaseModel):
    """Contract for out/themes.json."""

    app_id: str = "com.openai.chatgpt"
    window: Optional[DateWindow] = None
    generated_at: Optional[datetime] = None
    themes: list[ThemeRecord] = Field(default_factory=list)

    @field_validator("themes")
    @classmethod
    def _cap_themes(cls, themes: list[ThemeRecord]) -> list[ThemeRecord]:
        if len(themes) > 5:
            raise ValueError("at most 5 themes allowed")
        return themes


class QuoteRecord(BaseModel):
    text: str
    theme: str
    rating: Optional[int] = None
    review_id: Optional[str] = None


class ActionRecord(BaseModel):
    title: str
    rationale: str = ""
    theme: str


class TopThemeSummary(BaseModel):
    label: str
    summary: str = ""
    review_count: int = 0


class SelectionResult(BaseModel):
    """Contract for out/selection.json."""

    top_themes: list[TopThemeSummary] = Field(default_factory=list)
    quotes: list[QuoteRecord] = Field(default_factory=list)
    actions: list[ActionRecord] = Field(default_factory=list)

    @field_validator("top_themes")
    @classmethod
    def _top_three(cls, themes: list[TopThemeSummary]) -> list[TopThemeSummary]:
        if len(themes) > 3:
            raise ValueError("pulse highlights at most Top 3 themes")
        return themes

    @field_validator("quotes")
    @classmethod
    def _three_quotes(cls, quotes: list[QuoteRecord]) -> list[QuoteRecord]:
        if quotes and len(quotes) != 3:
            raise ValueError("exactly 3 quotes required when selection is populated")
        return quotes

    @field_validator("actions")
    @classmethod
    def _three_actions(cls, actions: list[ActionRecord]) -> list[ActionRecord]:
        if actions and len(actions) != 3:
            raise ValueError("exactly 3 actions required when selection is populated")
        return actions


class DocRef(BaseModel):
    id: Optional[str] = None
    url: Optional[str] = None


class EmailDraftRef(BaseModel):
    id: Optional[str] = None


class PulseResult(BaseModel):
    """Contract for out/pulse.json."""

    product: str = "ChatGPT (Android)"
    app_id: str = "com.openai.chatgpt"
    window: Optional[DateWindow] = None
    generated_at: Optional[datetime] = None
    top_themes: list[TopThemeSummary] = Field(default_factory=list)
    quotes: list[QuoteRecord] = Field(default_factory=list)
    actions: list[ActionRecord] = Field(default_factory=list)
    word_count: int = 0
    markdown: str = ""
    doc: DocRef = Field(default_factory=DocRef)
    email_draft: EmailDraftRef = Field(default_factory=EmailDraftRef)
