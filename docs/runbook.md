# Operator runbook — AI Review Pulsator

## Weekly flow (what one run does)

1. **Acquire** public ChatGPT Play reviews (`com.openai.chatgpt`, `en`/`in`)
2. **Normalize + scrub** → `data/processed/reviews.cleaned.json`
3. **Theme / select / compose** (Groq classify + Gemini generate) → `out/pulse.*`
4. **Validate** hard caps (≤5 themes, 3 quotes, 3 actions, ≤250 words)
5. **Append** pulse to the rolling Google Doc via MCP
6. **Create** an unsent Gmail draft (Doc link + short summary) — human sends

Local equivalent of the scheduled job:

```bash
pulsator run --require-mcp
```

## Phase 4 — Scheduler

| Item | Value |
| --- | --- |
| Host (cloud) | GitHub Actions `.github/workflows/weekly-pulse.yml` |
| Cadence | Mondays **09:00 UTC** — automatic (no manual click) |
| Command | `pulsator run --require-mcp` |
| Host (Mac) | `./scripts/install_macos_weekly_launchd.sh` → Mon **14:30** local |
| Manual rescue | Actions → **Weekly Pulse** → Run workflow |
| Alt host | Railway cron / `POST /run` (same secrets) |

### One-time: enable unattended runs

**Cloud** (runs even if your laptop is off):

```bash
gh auth refresh -h github.com   # if gh auth expired
./scripts/setup_github_secrets.sh
```

**Mac** (uses this machine’s `.env`):

```bash
./scripts/install_macos_weekly_launchd.sh
```

After either path is set up, you do **not** need to run `pulsator` weekly by hand.

### Required GitHub Actions secrets

| Secret | Purpose |
| --- | --- |
| `GROQ_API_KEY` | Theme classification |
| `GEMINI_API_KEY` | Quotes / actions / pulse prose |
| `GOOGLE_DOCS_DOCUMENT_ID` | Rolling Doc id (append only) |
| `EMAIL_TO` | Gmail draft recipient |
| `MCP_SERVER_URL` | Optional; defaults to Railway MCP `/mcp` |
| `MCP_API_KEY` | Optional; if Railway MCP requires it |
| `ACQUIRE_MAX_REVIEWS` | Optional scrape cap for rescue runs |

`GOOGLE_REFRESH_TOKEN` lives on the **Railway MCP server**, not in this repo’s Actions secrets.

### Artifact retention

- Actions uploads `out/` + cleaned corpus for **28 days** (~4 weeks).
- Re-running the same ISO week **appends another Doc section**; use `--stage` filters if you only need to recover publish/draft.

### Failure visibility

- Scheduled runs use `REQUIRE_MCP=true` / `--require-mcp` so Doc/Gmail failures **fail the job** (red × in Actions).
- Soft-fail (`require_mcp: false`) is for local iteration only.

### Idempotency / re-runs

| Situation | What to do |
| --- | --- |
| Mid-week re-run | `workflow_dispatch` with `acquire_mode=live` or `file` |
| Delivery only | Local: `pulsator run --stage publish_docs` then `--stage draft_email` |
| Scrape too heavy | Set `ACQUIRE_MODE=file` or `ACQUIRE_MAX_REVIEWS` |

## Privacy before share

- Confirm scrubbed corpus (no emails/phones/usernames) before treating Doc/email as shareable.
- Draft only — review the Gmail draft, then send manually.
