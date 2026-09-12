"""Load and validate runtime configuration from config.yaml."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, field_validator


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = REPO_ROOT / "config.yaml"

STAGE_IDS = (
    "acquire",
    "normalize",
    "scrub",
    "theme",
    "select",
    "compose",
    "publish_docs",
    "draft_email",
)

# Graph node ids (ingest is acquire → normalize → scrub; pulse is theme → validate)
GRAPH_NODE_IDS = (
    "acquire",
    "normalize",
    "scrub",
    "theme",
    "select",
    "compose",
    "validate",
    "publish",
    "draft_email",
)


class AcquireConfig(BaseModel):
    mode: Literal["live", "file"] = "file"
    client: str = "google-play-scraper"
    sort: str = "newest"
    max_reviews: int = 2000
    raw_glob: str = "data/raw/play_reviews_*.json"
    fixture_path: str = "data/raw/play_reviews_fixture.json"


class PathsConfig(BaseModel):
    raw_dir: str = "data/raw"
    interim_dir: str = "data/interim"
    processed_dir: str = "data/processed"
    out_dir: str = "out"
    prompts_dir: str = "prompts"
    cleaned_reviews: str = "data/processed/reviews.cleaned.json"
    cleaned_reviews_csv: str = "data/processed/reviews.cleaned.csv"
    normalized_reviews: str = "data/interim/reviews.normalized.json"
    themes: str = "out/themes.json"
    selection: str = "out/selection.json"
    pulse_md: str = "out/pulse.md"
    pulse_json: str = "out/pulse.json"
    run_log: str = "out/run.log"


class LlmEndpointConfig(BaseModel):
    """One LLM endpoint (classify or generate) with rate-limit metadata."""

    provider: str
    model: str
    temperature: float = 0.0
    requests_per_minute: int = 30
    requests_per_day: int = 1000
    tokens_per_minute: int = 8000
    tokens_per_day: int = 200000


class McpConfig(BaseModel):
    """Railway Google Workspace MCP (Streamable HTTP) for Docs append + Gmail draft."""

    # Public URL; client normalizes to …/mcp. Override with MCP_SERVER_URL.
    url: str = "https://mcp-server-google-production.up.railway.app/mcp"
    # Optional shared secret; prefer MCP_API_KEY env over committing here.
    api_key: str = ""
    # Existing Google Doc id (or Docs URL). MCP has append only — no create tool.
    # Prefer GOOGLE_DOCS_DOCUMENT_ID env.
    docs_document_id: str = ""
    email_subject_template: str = "ChatGPT Play Pulse — {iso_week}"


class LangChainConfig(BaseModel):
    """Dual-LLM setup: Groq classifies reviews; Gemini generates pulse content."""

    tracing: bool = False
    require_mcp: bool = False
    classify: LlmEndpointConfig = Field(
        default_factory=lambda: LlmEndpointConfig(
            provider="groq",
            model="openai/gpt-oss-120b",
            temperature=0.0,
            requests_per_minute=30,
            requests_per_day=1000,
            tokens_per_minute=8000,
            tokens_per_day=200000,
        )
    )
    generate: LlmEndpointConfig = Field(
        default_factory=lambda: LlmEndpointConfig(
            provider="gemini",
            model="gemini-2.5-flash",
            temperature=0.2,
            requests_per_minute=15,
            requests_per_day=1500,
            tokens_per_minute=1000000,
            tokens_per_day=10000000,
        )
    )
    # How many cleaned reviews Groq labels per run (stratified sample)
    classify_sample_size: int = 900
    classify_batch_size: int = 20


class AppConfig(BaseModel):
    app_id: str = "com.openai.chatgpt"
    play_url: str = (
        "https://play.google.com/store/apps/details?id=com.openai.chatgpt&hl=en_IN"
    )
    lang: str = "en"
    country: str = "in"
    acquire: AcquireConfig = Field(default_factory=AcquireConfig)
    lookback_weeks: int = 10
    max_themes: int = 5
    pulse_top_themes: int = 3
    pulse_quotes: int = 3
    pulse_actions: int = 3
    max_pulse_words: int = 250
    email_to: str = "you@example.com"
    docs_title_template: str = "ChatGPT Play Pulse — {iso_week}"
    paths: PathsConfig = Field(default_factory=PathsConfig)
    langchain: LangChainConfig = Field(default_factory=LangChainConfig)
    mcp: McpConfig = Field(default_factory=McpConfig)

    @field_validator("lookback_weeks")
    @classmethod
    def _lookback_in_range(cls, value: int) -> int:
        if value < 8 or value > 12:
            raise ValueError("lookback_weeks must be within 8–12")
        return value

    def resolve(self, relative: str | Path) -> Path:
        """Resolve a config-relative path against the repo root."""
        path = Path(relative)
        if path.is_absolute():
            return path
        return (REPO_ROOT / path).resolve()

    def fixture_path(self) -> Path:
        return self.resolve(self.acquire.fixture_path)


def load_config(path: str | Path | None = None) -> AppConfig:
    """Load YAML config into a typed AppConfig."""
    config_path = Path(path) if path else DEFAULT_CONFIG_PATH
    if not config_path.is_absolute():
        config_path = (REPO_ROOT / config_path).resolve()
    if not config_path.exists():
        raise FileNotFoundError(f"Config not found: {config_path}")

    raw: dict[str, Any]
    with config_path.open(encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle) or {}
        if not isinstance(loaded, dict):
            raise ValueError(f"Config root must be a mapping: {config_path}")
        raw = loaded

    return AppConfig.model_validate(raw)
