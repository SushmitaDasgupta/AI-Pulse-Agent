# AI Review Pulsator

Weekly one-page pulse from **public** Google Play reviews for ChatGPT (`com.openai.chatgpt`).

> **Status: P1–P3 ready. P4 weekly scheduler = GitHub Actions cron → full `pulsator run`.**

## Review data source

Reviews are fetched from the **public** ChatGPT Play Store listing (no Play Console / login):

https://play.google.com/store/apps/details?id=com.openai.chatgpt&hl=en_IN

| Item | Value |
| --- | --- |
| App ID | `com.openai.chatgpt` |
| Locale | `lang=en`, `country=in` (from `hl=en_IN`) |
| Client | `google-play-scraper` |
| Live landing | `data/raw/play_reviews_<timestamp>.json` |
| Offline / CI | `acquire.mode: file` → latest `data/raw/` export or `data/raw/play_reviews_fixture.json` |

**Not used:** Google Play Console, Play Developer API, Google-account store login.

## Install

Requires **Python 3.11+** (verified with 3.12).

```bash
# Example with Homebrew Python 3.12:
#   /opt/homebrew/opt/python@3.12/bin/python3.12 -m venv .venv
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .   # enables the `pulsator` console script
```

Optional: copy `.env.example` → `.env` and set **both** `GROQ_API_KEY` (classification) and `GEMINI_API_KEY` (generation). **P2 also runs offline** with the deterministic catalog path when keys are missing.

## Acquire notes

```bash
# Offline / CI (override with ACQUIRE_MODE=file)
# acquire.mode: file

# Live public fetch
# Set acquire.mode: live in config.yaml (or ACQUIRE_MODE=live), then:
pulsator run --stage ingest
# On live failure, acquire retries then falls back to the latest data/raw export.
```

Raw exports include provenance: `app_id`, `lang`/`country`, `play_url`, `fetched_at`, `client`.

## CLI

```bash
pulsator run --help
pulsator stages

# Full weekly path (ingest + pulse + Doc + Gmail draft)
pulsator run --require-mcp

# Ingest only (acquire → normalize → scrub)
pulsator run --stage ingest

# Pulse only on existing cleaned corpus (theme → select → compose → validate)
pulsator run --stage pulse

# Individual stages
pulsator run --stage acquire
pulsator run --stage normalize
pulsator run --stage scrub
pulsator run --stage theme
pulsator run --stage select
pulsator run --stage compose
pulsator run --stage validate

# Phase 3 delivery (requires MCP env + GOOGLE_DOCS_DOCUMENT_ID + email_to)
pulsator run --stage publish_docs
pulsator run --stage draft_email
```

## Phase 4 — Weekly scheduler

Unattended Monday run — **no manual kickoff** once secrets/LaunchAgent are set:

| Item | Value |
| --- | --- |
| Cloud cron | [`.github/workflows/weekly-pulse.yml`](.github/workflows/weekly-pulse.yml) — Mondays **09:00 UTC** |
| Mac cron | `./scripts/install_macos_weekly_launchd.sh` — Mondays **14:30** local |
| Command | `pulsator run --require-mcp` |
| One-time cloud setup | `gh auth refresh -h github.com && ./scripts/setup_github_secrets.sh` |
| Artifacts | Actions uploads `out/` for **28 days** |

**GitHub secrets:** `GROQ_API_KEY`, `GEMINI_API_KEY`, `GOOGLE_DOCS_DOCUMENT_ID`, `EMAIL_TO` (optional: `MCP_SERVER_URL`, `MCP_API_KEY`, `ACQUIRE_MAX_REVIEWS`).

Re-running the same ISO week **appends another Doc section**. Email remains **draft-only** (send manually). Details: [`docs/runbook.md`](docs/runbook.md).

## Phase 3 MCP (Railway)

| Item | Value |
| --- | --- |
| MCP URL | `https://mcp-server-google-production.up.railway.app/mcp` |
| Tools used | `google_docs_append_content`, `gmail_draft_email` |
| Env | `MCP_SERVER_URL`, `MCP_API_KEY` (if set), `GOOGLE_DOCS_DOCUMENT_ID`, `EMAIL_TO` |
| Config | `mcp.docs_document_id` (optional), `langchain.require_mcp` / `REQUIRE_MCP` |

The MCP server **appends** to an existing Google Doc (it cannot create one). Create a Doc once, paste its id into `.env`, then run publish/draft stages.

## Pipeline stage IDs

| Stage | ID | Phase |
| --- | --- | --- |
| Acquire public reviews | `acquire` | P1 |
| Normalize fields | `normalize` | P1 |
| Scrub PII | `scrub` | P1 |
| Theme (≤5) | `theme` | P2 |
| Select Top 3 / quotes / actions | `select` | P2 |
| Compose ≤250-word pulse | `compose` | P2 |
| Validate quote/theme/word gates | `validate` | P2 |
| Publish Google Doc via MCP | `publish_docs` | P3 |
| Create Gmail draft via MCP | `draft_email` | P3 |
| Weekly cron → full graph | GitHub Actions | P4 |

**LangGraph:** `acquire → normalize → scrub → theme → select → compose → validate → publish → draft_email`

## Artifact paths

| Artifact | Path |
| --- | --- |
| Raw / fixture | `data/raw/` |
| Normalized | `data/interim/reviews.normalized.json` |
| Cleaned | `data/processed/reviews.cleaned.json` (+ `.csv`) |
| Themes | `out/themes.json` |
| Selection | `out/selection.json` |
| Pulse | `out/pulse.md`, `out/pulse.json` |
| Run log | `out/run.log` |

## Tests

```bash
pytest -q
# Optional live smoke:
PULSATOR_LIVE=1 pytest -q -m network
```

## Config

See `config.yaml` for `play_url`, `app_id`, `acquire`, lookback, caps, and LangChain settings. Scheduler overrides: `ACQUIRE_MODE`, `ACQUIRE_MAX_REVIEWS`, `REQUIRE_MCP`.

## Docs

- [`docs/problemStatement.md`](docs/problemStatement.md)
- [`docs/architecture.md`](docs/architecture.md)
- [`docs/implementation-plan.md`](docs/implementation-plan.md)
- [`docs/runbook.md`](docs/runbook.md)
