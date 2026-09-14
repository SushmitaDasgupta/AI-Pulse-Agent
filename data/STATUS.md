# Data status

## Live reviews downloaded

| Item | Value |
| --- | --- |
| Source | https://play.google.com/store/apps/details?id=com.openai.chatgpt&hl=en_IN |
| Client | google-play-scraper (`en` / `in`) |
| Raw / in-window reviews | **89,800** |
| After Phase-1 quality filters | **9,428** |
| Filters | Drop `<8` words; keep English-only body text |
| Dropped short (`<8` words) | **78,483** |
| Dropped non-English | **1,889** |
| Date span | **2026-08-26 → 2026-09-09** (~15 days) |
| Target 8-week window | 2026-07-16 → 2026-09-10 |
| Full 8-week coverage | **Not yet** — public feed rate-limited (resume stopped after empty-page retries) |

## Phase-2 pulse (latest)

| Item | Value |
| --- | --- |
| Command | `pulsator run --stage pulse` |
| Classify LLM | **Groq** `openai/gpt-oss-120b` (`GROQ_API_KEY`) |
| Generate LLM | **Gemini** `gemini-2.5-flash` (`GEMINI_API_KEY`) |
| Re-run needed? | **Yes — re-run P2** after both keys are set (P1 corpus unchanged) |
| Themes | ≤5 catalog themes in `out/themes.json` |
| Quotes / actions | Gemini-generated (verbatim quote gate) in `out/selection.json` |
| Pulse | `out/pulse.md` / `out/pulse.json` (≤250 words) |

## Phase-3 MCP delivery

| Item | Value |
| --- | --- |
| MCP URL | `https://mcp-server-google-production.up.railway.app/mcp` |
| Tools | `google_docs_append_content`, `gmail_draft_email` |
| Needs | `GOOGLE_DOCS_DOCUMENT_ID`, `EMAIL_TO`, optional `MCP_API_KEY` |
| Live smoke | Done (Doc append + Gmail draft IDs in `out/pulse.json`) |

## Phase-4 Weekly scheduler

| Item | Value |
| --- | --- |
| Workflow | `.github/workflows/weekly-pulse.yml` |
| Cadence | Mondays 09:00 UTC |
| Command | `pulsator run --require-mcp` |
| Local dry-run | `--require-mcp` publish + draft verified |
| Actions secrets | Set `GROQ_API_KEY`, `GEMINI_API_KEY`, `GOOGLE_DOCS_DOCUMENT_ID`, `EMAIL_TO` then Run workflow |


## Open these files

- `data/raw/play_reviews_latest.json`
- `data/interim/reviews.normalized.json`
- `data/processed/reviews.cleaned.json`
- `data/processed/reviews.cleaned.csv`
- `out/themes.json`
- `out/selection.json`
- `out/pulse.md`

## Note

ChatGPT’s public listing feed is very high volume. Completing a full 8-week pull needs further resume passes after rate limits cool down. P2 runs on the current cleaned corpus without waiting for full coverage.
