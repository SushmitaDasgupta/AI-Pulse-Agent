# AI Review Pulsator

Turns **public Google Play reviews** for ChatGPT Android (`com.openai.chatgpt`) into a **weekly ≤250-word pulse** — top themes, verbatim user quotes, and action ideas — then appends it to a Google Doc and creates an unsent Gmail draft.

> **Status:** P1–P3 ready. P4 weekly scheduler = GitHub Actions cron → full `pulsator run`.

---

## What this project does

Every week the system:

1. **Fetches** recent public Play Store reviews (no Console login).
2. **Classifies** them into a fixed theme catalog (login, reliability, image, paywall, quality, praise).
3. **Generates themes** — up to 5 themes with counts, shares, and short descriptions.
4. **Builds the pulse report** — Top 3 pain themes, 3 verbatim quotes, 3 action ideas, composed into ≤250 words.
5. **Delivers** — appends the pulse to a Google Doc and drafts a Gmail email (never auto-sends).

Stakeholders get a one-page note they can scan in minutes: *what users care about, what they said, and what to do next*.

---

## How it works (pipeline)

```text
Public Play listing
       │
       ▼
  acquire → normalize → scrub          (deterministic ingest; no LLM)
       │
       ▼
  theme                                (classify + aggregate ≤5 themes)
       │
       ▼
  select                               (Top 3 themes + quotes + actions)
       │
       ▼
  compose → validate                   (≤250-word pulse; hard gates)
       │
       ▼
  publish_docs → draft_email           (MCP → Google Doc + Gmail draft)
```

| Stage | What happens | Artifact |
| --- | --- | --- |
| **Acquire** | Live fetch via `google-play-scraper`, or offline file/fixture | `data/raw/play_reviews_*.json` |
| **Normalize** | Canonical review schema | `data/interim/reviews.normalized.json` |
| **Scrub** | PII redact; drop empty/short/non-English | `data/processed/reviews.cleaned.json` |
| **Theme** | Keyword baseline + Groq batch labels → ≤5 themes; Gemini enriches descriptions | `out/themes.json` |
| **Select** | Rank Top 3 pain themes; pick/generate quotes & action ideas | `out/selection.json` |
| **Compose** | Stakeholder markdown (themes / quotes / actions), optionally LLM-rewritten & shortened | `out/pulse.md`, `out/pulse.json` |
| **Validate** | ≤5 themes, exactly 3 quotes & 3 actions, quotes ⊆ cleaned text, ≤250 words | fail run if gates break |
| **Publish** | MCP `google_docs_append_content` — ISO-week section on an existing Doc | Doc URL |
| **Draft email** | MCP `gmail_draft_email` — body with themes, actions, Doc link (**draft only**) | Gmail draft |

**LangGraph** wires the stages: `acquire → normalize → scrub → theme → select → compose → validate → publish → draft_email` (`src/agent/graph.py`).

---

## LangChain and the two LLMs

The agent core is built with **LangChain** (chat models + message prompts) and orchestrated with **LangGraph** (one node per stage). Versioned prompts live under `prompts/`. Deterministic ingest/scrub and MCP delivery stay outside the LLM when possible; missing API keys fall back to keyword/catalog paths so the pipeline still runs offline.

| Role | Provider | Default model | Env key | Used for |
| --- | --- | --- | --- | --- |
| **Classify** | Groq (`ChatGroq`) | `openai/gpt-oss-120b` | `GROQ_API_KEY` | Batch-label a stratified sample of reviews into catalog `theme_id`s (`theme` stage) |
| **Generate** | Gemini (`ChatGoogleGenerativeAI`) | `gemini-2.5-flash` | `GEMINI_API_KEY` | Theme descriptions, quote/action proposals, pulse prose + shorten (`theme` / `select` / `compose`) |

**Why two models:** Groq’s free-tier throughput fits **batch classification** (~900 reviews in batches of ~20). Gemini fits **stakeholder-facing generation** (descriptions, quotes, actions, pulse copy). Config lives under `langchain.classify` / `langchain.generate` in `config.yaml`; factories in `src/agent/llm.py`.

| Chain module | LLM touchpoints |
| --- | --- |
| `src/agent/chains/theme.py` | Groq classify + Gemini theme descriptions |
| `src/agent/chains/select.py` | Gemini quotes & action ideas (quotes must be substrings of cleaned reviews) |
| `src/agent/chains/compose.py` | Gemini rewrite + shorten of the pulse body |

Email draft text itself is **deterministic** (no LLM) — themes, actions, Doc URL, and a “Draft only” footer.

---

## Review data source

Reviews come from the **public** ChatGPT Play Store listing (no Play Console / login):

https://play.google.com/store/apps/details?id=com.openai.chatgpt&hl=en_IN

| Item | Value |
| --- | --- |
| App ID | `com.openai.chatgpt` |
| Locale | `lang=en`, `country=in` (from `hl=en_IN`) |
| Client | `google-play-scraper` |
| Live landing | `data/raw/play_reviews_<timestamp>.json` |
| Offline / CI | `acquire.mode: file` → latest `data/raw/` export or `data/raw/play_reviews_fixture.json` |

**Not used:** Google Play Console, Play Developer API, Google-account store login.

---

## Install

Requires **Python 3.11+** (verified with 3.12).

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .   # enables the `pulsator` console script
```

Optional: copy `.env.example` → `.env` and set **both** `GROQ_API_KEY` (classification) and `GEMINI_API_KEY` (generation). Pulse stages also run offline with the deterministic catalog path when keys are missing.

---

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

### Acquire notes

```bash
# Offline / CI: acquire.mode: file (or ACQUIRE_MODE=file)
# Live: acquire.mode: live in config.yaml (or ACQUIRE_MODE=live)
pulsator run --stage ingest
# On live failure, acquire retries then falls back to the latest data/raw export.
```

Raw exports include provenance: `app_id`, `lang`/`country`, `play_url`, `fetched_at`, `client`.

---

## Phase 4 — Weekly scheduler

Unattended Monday run — no manual kickoff once secrets/LaunchAgent are set:

| Item | Value |
| --- | --- |
| Cloud cron | [`.github/workflows/weekly-pulse.yml`](.github/workflows/weekly-pulse.yml) — Mondays **09:00 UTC** |
| Mac cron | `./scripts/install_macos_weekly_launchd.sh` — Mondays **14:30** local |
| Command | `pulsator run --require-mcp` |
| One-time cloud setup | `gh auth refresh -h github.com && ./scripts/setup_github_secrets.sh` |
| Artifacts | Actions uploads `out/` for **28 days** |

**GitHub secrets:** `GROQ_API_KEY`, `GEMINI_API_KEY`, `GOOGLE_DOCS_DOCUMENT_ID`, `EMAIL_TO` (optional: `MCP_SERVER_URL`, `MCP_API_KEY`, `ACQUIRE_MAX_REVIEWS`).

Re-running the same ISO week **appends another Doc section**. Email remains **draft-only** (send manually). Details: [`docs/runbook.md`](docs/runbook.md).

---

## Phase 3 MCP (Railway)

| Item | Value |
| --- | --- |
| MCP URL | `https://mcp-server-google-production.up.railway.app/mcp` |
| Tools used | `google_docs_append_content`, `gmail_draft_email` |
| Env | `MCP_SERVER_URL`, `MCP_API_KEY` (if set), `GOOGLE_DOCS_DOCUMENT_ID`, `EMAIL_TO` |
| Config | `mcp.docs_document_id` (optional), `langchain.require_mcp` / `REQUIRE_MCP` |

The MCP server **appends** to an existing Google Doc (it cannot create one). Create a Doc once, paste its id into `.env`, then run publish/draft stages.

---

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

---

## Tests

```bash
pytest -q
# Optional live smoke:
PULSATOR_LIVE=1 pytest -q -m network
```

---

## Config

See `config.yaml` for `play_url`, `app_id`, `acquire`, lookback, caps, and LangChain settings (`classify` / `generate`). Scheduler overrides: `ACQUIRE_MODE`, `ACQUIRE_MAX_REVIEWS`, `REQUIRE_MCP`.

---

## Docs

- [`docs/problemStatement.md`](docs/problemStatement.md)
- [`docs/architecture.md`](docs/architecture.md)
- [`docs/implementation-plan.md`](docs/implementation-plan.md)
- [`docs/runbook.md`](docs/runbook.md)
