# Deployment — Vercel (frontend) + Railway (backend)

Deploy the React pulse UI from `web/` on **Vercel**, and the Python pulse service from the repo root on **Railway**.

| Surface | Host | Source | Role |
| --- | --- | --- | --- |
| Frontend | Vercel | `web/` | Stakeholder UI (themes, quotes, actions, email compose) |
| Backend | Railway | repo root (`Dockerfile`, `railway.toml`) | Health + optional `POST /run` pulse trigger |
| Google Workspace MCP | Railway (separate service) | external | Docs append + Gmail draft tools |

Weekly unattended runs default to **GitHub Actions** ([`docs/runbook.md`](./runbook.md)). Railway is an alternate host for the same CLI image.

---

## Prerequisites

- GitHub repo with this project pushed
- [Vercel](https://vercel.com) account (GitHub connected)
- [Railway](https://railway.app) account
- Secrets from [`.env.example`](../.env.example) (never commit `.env`)

---

## 1. Backend — Railway

The service is already wired for Railway:

- [`Dockerfile`](../Dockerfile) — Python 3.12 image, installs deps, starts `python -m src.serve`
- [`railway.toml`](../railway.toml) — Dockerfile builder, healthcheck `/health`, start command `python -m src.serve`

### Create the service

1. In Railway: **New Project** → **Deploy from GitHub repo** → select this repository.
2. Confirm build uses the **Dockerfile** at the repo root (matches `railway.toml`).
3. Generate a public domain (Settings → Networking → **Generate Domain**).
4. Note the HTTPS base URL, e.g. `https://ai-review-pulsator-production.up.railway.app`.

### Environment variables

Set these in the Railway service **Variables** tab (same names as local `.env`):

| Variable | Required | Purpose |
| --- | --- | --- |
| `GROQ_API_KEY` | Yes (live pulse) | Theme classification |
| `GEMINI_API_KEY` | Yes (live pulse) | Quotes / actions / pulse prose |
| `MCP_SERVER_URL` | Yes for Doc/Gmail | Default: `https://mcp-server-google-production.up.railway.app/mcp` |
| `MCP_API_KEY` | If MCP requires it | `Authorization: Bearer …` |
| `GOOGLE_DOCS_DOCUMENT_ID` | Yes for publish | Existing Doc id (MCP appends only) |
| `EMAIL_TO` | Yes for draft | Gmail draft recipient |
| `REQUIRE_MCP` | Recommended `true` | Hard-fail Doc/Gmail on triggered runs |
| `ACQUIRE_MODE` | Optional | `live` or `file` |
| `ACQUIRE_MAX_REVIEWS` | Optional | Scrape cap |
| `PORT` | No | Railway injects this; `src.serve` reads it (default `8080`) |

Do **not** put `GOOGLE_REFRESH_TOKEN` on this service — that belongs on the **MCP** Railway app.

### HTTP API (this service)

| Method | Path | Behavior |
| --- | --- | --- |
| `GET` | `/` or `/health` | `{"status":"ok","service":"ai-pulse-agent"}` |
| `POST` | `/run` | Starts full graph in a background thread; `202 {"status":"started"}` (sets `REQUIRE_MCP=true` if unset) |

### Smoke checks

```bash
# Health (replace with your Railway URL)
curl -sS https://YOUR-SERVICE.up.railway.app/health

# Trigger a full pulse (async; watch Railway logs)
curl -sS -X POST https://YOUR-SERVICE.up.railway.app/run
```

Expect health `200`. For `/run`, watch deploy logs for `[serve] pulse complete` or `[serve] pulse failed: …`.

### Optional: Railway cron

Prefer GitHub Actions for the weekly schedule. If you use Railway cron / one-off instead:

- Command: `pulsator run --require-mcp`  
  **or** `POST /run` against this service with `REQUIRE_MCP=true` in env.

---

## 2. Frontend — Vercel

The UI lives in [`web/`](../web/) (Vite + React). Build output is static files in `web/dist`.

> **P6 note:** The UI is currently **seeded** from local pulse data (no live backend wire-up). Deploying to Vercel still works as a static site; API env vars are for a later hookup.

### Create the project

1. In Vercel: **Add New…** → **Project** → import this GitHub repository.
2. Configure:

| Setting | Value |
| --- | --- |
| **Root Directory** | `web` |
| **Framework Preset** | Vite (auto-detected) |
| **Build Command** | `npm run build` |
| **Output Directory** | `dist` |
| **Install Command** | `npm install` |

3. Deploy. Vercel will assign a URL like `https://ai-review-pulsator.vercel.app`.

### Environment variables (optional / future)

Not required for the current UI-only seed. When the frontend calls Railway:

| Variable | Example | Purpose |
| --- | --- | --- |
| `VITE_API_BASE_URL` | `https://YOUR-SERVICE.up.railway.app` | Base URL for `GET /health`, `POST /run`, etc. |

Rebuild after adding `VITE_*` vars (they are inlined at build time).

### Local preview of the production build

```bash
cd web
npm install
npm run build
npm run preview
```

---

## 3. Connect frontend ↔ backend (when wiring live)

1. Deploy Railway first; confirm `GET /health`.
2. Set `VITE_API_BASE_URL` on Vercel to the Railway HTTPS origin (no trailing slash).
3. Redeploy the Vercel project.
4. If the browser calls Railway directly, add CORS headers on `src.serve` (or put a small API proxy on Vercel) — **not implemented yet**.

Until that exists, treat Vercel as the static pulse viewer and Railway / Actions as the pipeline runners.

---

## 4. Related services

### Google Workspace MCP (already on Railway)

| Item | Value |
| --- | --- |
| Health | `https://mcp-server-google-production.up.railway.app/health` |
| MCP endpoint | `https://mcp-server-google-production.up.railway.app/mcp` |
| Used by | Pulsator `publish_docs` / `draft_email` stages |

Create the rolling Google Doc once; put its id in `GOOGLE_DOCS_DOCUMENT_ID` on the **pulse** Railway service (and GitHub Actions secrets).

### Weekly scheduler

| Host | Doc |
| --- | --- |
| GitHub Actions (default) | [`docs/runbook.md`](./runbook.md) |
| Railway cron / `POST /run` | This file, §1 |

---

## 5. Checklist

**Railway**

- [ ] Service builds from root `Dockerfile`
- [ ] Public domain generated
- [ ] `GROQ_API_KEY`, `GEMINI_API_KEY` set
- [ ] `MCP_SERVER_URL`, `GOOGLE_DOCS_DOCUMENT_ID`, `EMAIL_TO` set
- [ ] `curl …/health` returns `ok`
- [ ] Optional: `POST /run` succeeds in logs

**Vercel**

- [ ] Root Directory = `web`
- [ ] Build succeeds (`tsc -b && vite build`)
- [ ] Site loads at the Vercel URL
- [ ] Optional later: `VITE_API_BASE_URL` → Railway origin + redeploy

**Secrets hygiene**

- [ ] No `.env` committed
- [ ] MCP Google OAuth tokens stay on the MCP Railway service only

---

## 6. Troubleshooting

| Symptom | Check |
| --- | --- |
| Railway healthcheck fails | Logs for import/crash; confirm `PORT` and `CMD` match `python -m src.serve` |
| `/run` starts but pulse fails | Missing LLM/MCP env; see `[serve] pulse failed` in logs |
| Doc/Gmail soft-skip | Set `REQUIRE_MCP=true` or use `--require-mcp` |
| Vercel build fails | Root Directory must be `web`; Node 20+ recommended |
| Blank / wrong pulse on Vercel | UI still uses seed data until API wire-up |
| CORS errors from browser → Railway | Expected until CORS or a Vercel rewrite/proxy is added |

---

## See also

- [`docs/runbook.md`](./runbook.md) — weekly operator flow and GitHub Actions secrets
- [`README.md`](../README.md) — local CLI install and stage IDs
- [`.env.example`](../.env.example) — full env reference
