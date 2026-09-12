# AI Review Pulsator — Evaluation Plan

How we know each phase of [`implementation-plan.md`](./implementation-plan.md) actually works — and when the project is done.

**Eval layers**

| Layer | What it proves | When |
| --- | --- | --- |
| **Gate** | Phase exit criteria / hard constraints (pass/fail) | End of each phase |
| **Automated** | Unit + contract + validator tests | CI / P4 |
| **Smoke** | Live acquire + MCP (env-dependent) | P1 / P3 manually or nightly |
| **Quality** | Human rubric on pulse usefulness | After P2 (and before stakeholder share) |

Related: [`edge-case.md`](./edge-case.md) for blocker/degrade cases; [`architecture.md`](./architecture.md) for contracts.

---

## 1. Success criteria (project-level DoD)

Score **pass/fail**. All must pass for v1 release.

| ID | Criterion | Eval method | Pass if |
| --- | --- | --- | --- |
| S1 | Reviews imported for ~8–12 weeks from ChatGPT Play listing | Inspect `data/raw/` provenance + `reviews.cleaned.json` window vs `lookback_weeks`; app id `com.openai.chatgpt` | Window covered; source = public listing / saved export of that feed (not Console) |
| S2 | Reviews clustered into ≤5 themes | Assert on `out/themes.json` | `len(themes) ≤ 5` and ≥ 1 |
| S3 | One-page pulse: Top 3 themes, 3 verbatim quotes, 3 actions, ≤250 words | Assert on `out/selection.json` + `out/pulse.md` / `pulse.json` | Counts exact; quotes ⊆ cleaned text; word count ≤ 250 |
| S4 | Pulse published to Google Docs via MCP | Smoke: Doc URL/ID in `run.log` / `pulse.json`; open Doc | Content matches pulse; MCP path (no custom Docs REST client) |
| S5 | Gmail draft via MCP to self/alias | Smoke: draft ID logged; draft visible, unsent | Body has note or Doc pointer |
| S6 | No PII; no illicit scraping; MCP-first | Scrub tests + artifact scan + code/docs review | No usernames/emails/device IDs in deliverables; acquire = public listing client only |

**Operational DoD:** a new operator can follow the runbook, run `pulsator run`, and get Doc + draft without Play Console or bespoke Google API code.

---

## 2. Phase-gated evaluation

### P0 — Skeleton

| Check | Type | Pass |
| --- | --- | --- |
| `pulsator run --help` in clean venv | Automated / manual | Exit 0; stages listed |
| Config loads (`play_url`, `app_id`, `acquire`, caps) | Automated | No parse errors; fixture path resolves |
| Graph stub E2E without LLM/MCP | Automated | Exit 0 |
| Schema modules import | Automated | Import OK |

**P0 gate:** all four exit criteria checked.

---

### P1 — Ingest & scrub

| Check | Type | Metric / assert |
| --- | --- | --- |
| Live acquire for `com.openai.chatgpt` (`en`/`in`) **or** file fallback | Smoke / CI file-mode | Raw file written; provenance includes app id, lang/country, timestamp |
| In-window filter | Automated | All cleaned `date` within `[run_date − lookback_weeks, run_date]` |
| Field mapping | Automated | Fixture: `score`→`rating`, `content`→`text`, `at`→`date` |
| Empty body dropped | Automated | No empty `text` in cleaned |
| PII stripped | Automated | Planted `userName`/email/phone absent from cleaned; body redactions applied |
| Counts logged | Contract | `run.log` has fetched → in-window → cleaned |

**P1 gate:** cleaned corpus exists for listing URL; S1 progress; scrub tests green.

**Smoke (optional in CI):** mark live acquire `@network` — skip offline; required once before calling P1 “done.”

---

### P2 — LangChain pulse

| Check | Type | Pass |
| --- | --- | --- |
| Artifacts written | Automated | `themes.json`, `selection.json`, `pulse.md`, `pulse.json` exist |
| Theme cap | Automated | ≤5 themes |
| Top themes in pulse | Automated | Pulse references ≤3 top themes (or `min(3, n_themes)`) |
| Quote count + fidelity | Automated | Exactly 3; each is substring of some cleaned review `text` |
| Distinct quote sources | Automated | 3 distinct `review_id`s (per edge-case Q7) |
| Action count + theme link | Automated | Exactly 3; each maps to a theme |
| Word budget | Automated | Stakeholder body ≤250 words |
| Required sections | Automated / checklist | Header, themes, quotes, actions present |
| Validator blocks bad quotes | Automated | Paraphrase fixture → non-zero exit; no publish tools called |

**P2 gate:** S2 + S3 pass on at least one real (or recorded) cleaned corpus.

**Quality rubric (human)** — score after automated gate:

| Dimension | 1 | 3 | 5 |
| --- | --- | --- | --- |
| **Theme salience** | Themes feel arbitrary | Mostly match volume/pain | Top themes clearly match what dominates the sample |
| **Quote usefulness** | Generic / weak | OK illustration | Specific, scannable, one-per-theme feel |
| **Action concreteness** | Vague (“improve UX”) | Somewhat actionable | Clear next step for Product/Support/Growth |
| **Scannability** | Dense / overlong feel | Readable | Leadership can absorb in ≤2 minutes |

**P2 quality bar:** average ≥ 3.5 / 5 across dimensions; no dimension = 1. Run on **2 raters** if possible (PM + eng).

---

### P3 — MCP delivery

| Check | Type | Pass |
| --- | --- | --- |
| Docs via MCP | Smoke | Doc created/updated; title matches template; body ≈ `pulse.md` |
| Gmail draft via MCP | Smoke | Draft to `email_to`; unsent; contains pulse or Doc link |
| IDs persisted | Automated (after smoke) | `pulse.json` / `run.log` have doc + draft ids |
| No primary Google REST client | Code review | Delivery goes through MCP tool wrappers |
| Soft-fail path | Automated (mocked) | MCP down + `require_mcp: false` → local pulse kept, warning, exit 0 |
| Hard-fail path | Automated (mocked) | `require_mcp: true` + MCP down → non-zero exit |
| Privacy on delivered artifacts | Manual spot-check | No PII in Doc/draft |

**P3 gate:** S4 + S5 on a real MCP-connected run once; mocks cover CI.

---

### P4 — Harden & runbook

| Check | Type | Pass |
| --- | --- | --- |
| Test suite coverage of scrub, quotes, words, theme cap | Automated | Tests exist and pass |
| Clean-machine reproduce | Manual | Follow runbook once end-to-end |
| DoD checklist | Manual | All S1–S6 checked |
| Risk mitigations present | Review | Public-only acquire, PII scrub, quote gate documented/coded |

**P4 gate:** project-level DoD complete.

---

## 3. Automated eval suite (target layout)

```text
tests/
  test_config.py
  test_normalize.py
  test_scrub.py
  test_window.py
  test_theme_schema.py
  test_quote_fidelity.py
  test_word_count.py
  test_validators_block_publish.py
  test_mcp_tools_mocked.py
fixtures/
  raw_with_pii.json
  raw_window_mix.json
  cleaned_golden.json
  selection_paraphrase.json   # must fail quote gate
  pulse_over_budget.md        # must fail or trigger retry-then-fail
```

### Core asserts (copy into validators + tests)

```text
assert app_id == "com.openai.chatgpt"
assert 8 <= lookback_weeks <= 12 or warn+clamp policy documented
assert len(themes) <= 5
assert len(quotes) == 3
assert all(q.text in cleaned_corpus_text for q in quotes)  # substring over cleaned reviews
assert len(actions) == 3
assert word_count(pulse_body) <= 250
assert no_pii(pulse_md) and no_pii(pulse_json)
```

### CI policy

| Job | Runs | Needs |
| --- | --- | --- |
| Unit + contract | Every PR | Fixtures only |
| Live acquire | Manual / scheduled | Network; may be flaky |
| MCP smoke | Manual | Docs/Gmail MCP auth |

---

## 4. Metrics dashboard (per weekly run)

Log to `out/run.log` (and optionally summarize in README eval notes):

| Metric | Good | Investigate |
| --- | --- | --- |
| `reviews_fetched` | > 0 | A3 empty fetch |
| `reviews_in_window` | ≥ `min_reviews_after_window` | Sparse window / max_reviews too low |
| `reviews_cleaned` | ≈ in-window minus empties | Over-dropping |
| `theme_count` | 1–5 | >5 = validator bug |
| `quote_validation_pass` | true | Hallucination / scrub mismatch |
| `pulse_word_count` | ≤ 250 | Compose retry failing |
| `acquire_mode` | `live` preferred | Chronic `file` = fetch reliability issue |
| `docs_ok` / `draft_ok` | true when MCP required | Auth / tool gaps |
| `exit_code` | 0 | Any blocker from edge-case list |

**Trend (optional):** over N weekly runs, % runs with `exit_code=0` and quality rubric ≥ 3.5 — target ≥ 80% once stable.

---

## 5. Eval scenarios by priority

### Must-pass (release blockers)

1. File-mode golden path: fixture → cleaned → pulse → validators green.  
2. Quote paraphrase rejected.  
3. PII not present in cleaned or pulse.  
4. Word count >250 fails after retry.  
5. Theme count >5 fails after repair attempt.  
6. Mocked MCP soft/hard fail respects `require_mcp`.

### Should-pass (before calling weekly “production”)

7. Live acquire once for listing URL → non-empty in-window set.  
8. Full graph with real LLM → human rubric ≥ 3.5.  
9. Real MCP Doc + draft once; IDs logged.  
10. Runbook followed on clean venv.

### Nice-to-have

11. LangSmith trace attached for one failing compose.  
12. Dual-rater agreement on rubric (±1).  
13. Re-run same ISO week idempotency notes (new raw file, Doc strategy).

---

## 6. Audience acceptance (lightweight)

Map to implementation-plan “who this helps” via a 5-minute read of `out/pulse.md` (or the Doc):

| Audience | Acceptance question | Pass |
| --- | --- | --- |
| Product / Growth | “Can I pick a next fix from the 3 actions?” | Yes without opening raw reviews |
| Support | “Do quotes match what users actually say?” | Quotes feel authentic / verified verbatim |
| Leadership | “Do I understand health in one page?” | Finished in ≤2 minutes; ≤250 words |

One **yes** from each role (or PM proxy for all three) closes quality eval for that build.

---

## 7. Scoring summary card (use at phase end)

```text
Phase: P__
Date:
Corpus: live | file  (path/url:)
Automated gates:  PASS / FAIL
S1–S6:  S1_ S2_ S3_ S4_ S5_ S6_
Quality avg (P2+):  __ / 5
MCP smoke (P3+):  PASS / SKIP / FAIL
Blockers open: (edge-case IDs)
Sign-off:
```

---

## 8. Traceability to implementation plan

| Plan phase | Primary eval | Unlocks |
| --- | --- | --- |
| P0 | CLI/config/graph stub gates | Foundation |
| P1 | Acquire + scrub + window asserts | S1, S6 (privacy baseline) |
| P2 | Artifact + validator + human rubric | S2, S3 |
| P3 | MCP smoke + mock require_mcp | S4, S5 |
| P4 | Full suite + runbook reproduce + DoD card | All S1–S6 |

---

## 9. Eval schedule

| When | Activity |
| --- | --- |
| End of each phase | Fill scoring summary card; do not start next phase on FAIL gates |
| Every PR (once tests exist) | Unit/contract suite |
| Once before demo / handoff | Live acquire + LLM pulse + MCP smoke + audience questions |
| Each weekly production run | Metrics row in `run.log`; spot-check quotes; privacy glance |

---

## 10. Out of scope for v1 eval

- Statistical theme accuracy vs large labeled gold set  
- A/B of embedding clustering vs LLM labeling  
- Auto-send email delivery rates  
- Play Console parity metrics  

Those can wait until the DoD checklist is green.
