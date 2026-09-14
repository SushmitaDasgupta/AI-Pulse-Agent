# AI Review Pulsator — Web UI

React frontend for the weekly ChatGPT Play pulse. Visuals follow the Stitch export in `../stitch_ai_review_pulsator_ui/` (Executive Pulse tokens).

## Run

```bash
cd web
npm install
npm run dev
```

Open the printed local URL (usually `http://localhost:5173`).

## What it shows

- Latest weekly pulse: top 3 themes, 3 verbatim quotes, 3 action ideas
- Meta strip (window, cleaned review count, word budget, status)
- Link to the rolling Google Doc
- **Run weekly pulse** — simulated pipeline stage chips (UI-only)
- **Send email** — compose + **Send now** with success toast (UI-only; no Gmail MCP)

Seed data mirrors `out/pulse.json`. No backend wiring in P6.
