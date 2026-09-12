# AI Review Pulsator — Problem Statement

## Overview

Build a weekly review-pulse system for the **ChatGPT** Android app on Google Play:

[ChatGPT on Google Play](https://play.google.com/store/apps/details?id=com.openai.chatgpt&hl=en_IN)

**Goal:** Turn raw mobile-store feedback into a weekly pulse your team can scan in minutes — what users care about, what they actually said, and what to do next.

Reviews are already public. The job is to **aggregate**, **theme**, **summarize**, and **deliver** that insight through familiar surfaces:

- **Google Docs** — for the written pulse
- **Gmail** — for a draft you can send yourself

…without handling credentials or REST wiring yourself.

---

## End-to-End Flow (What “Done” Looks Like)

1. **Pull** recent Play Store reviews for the product (within the rules below).
2. **Cluster** them into a small set of themes and distill a one-page weekly note.
3. **Publish** that note where stakeholders can read it (Google Docs).
4. **Create** a draft email to yourself (or an alias) that contains or links to that pulse (Gmail).

**Product URL:** https://play.google.com/store/apps/details?id=com.openai.chatgpt&hl=en_IN

---

## Deliverables

### Weekly one-page pulse must include

| Element | Requirement |
| --- | --- |
| **Top themes** | What people are talking about most |
| **Real user quotes** | Verbatim snippets from reviews — no invented wording |
| **Three action ideas** | Concrete next steps grounded in the themes |

### Final step

Send yourself a **draft email** containing this weekly note (or a clear pointer to it).

---

## Who This Helps

| Audience | Why |
| --- | --- |
| **Product / Growth** | Prioritize fixes and improvements from real signals |
| **Support** | Align messaging with what users are actually saying |
| **Leadership** | One-page health check without drowning in raw reviews |

---

## What You Must Build

1. **Import reviews** from roughly the last **8–12 weeks** (fields such as rating, title, text, date — whatever your export provides).
2. **Group reviews** into at most **5 themes** (examples: onboarding, KYC, payments, statements, withdrawals — pick what fits your product).
3. **Generate a weekly one-page note** with:
   - Top **3** themes (subset of your themes as appropriate)
   - **3** user quotes
   - **3** action ideas
4. **Draft an email** with the note to yourself or an alias.

---

## Integrations: Google Docs & Gmail via MCP

Use **MCP (Model Context Protocol)** servers for Google Docs and Gmail — for example, creating or updating the pulse document and creating the draft message — rather than integrating Google APIs directly (**no bespoke OAuth client + REST client code** as the primary integration path).

MCP servers expose tools your agent or app can call; lean on that pattern so Docs and Gmail stay consistent with the course tooling and avoid duplicating auth and HTTP plumbing.

> Choose MCP servers or connectors your environment provides for Docs and Gmail. The requirement is **MCP-first**, not “call Google APIs manually.”

---

## Key Constraints

| Constraint | Rule |
| --- | --- |
| **Reviews** | Use public review exports only — no scraping behind store logins or ToS-violating automation. |
| **Themes** | Maximum **5** themes for clustering; the written pulse highlights the **top 3**. |
| **Length** | Keep the note scannable and **≤250 words** where applicable. |
| **Privacy** | Do not include PII — no usernames, emails, device IDs, or other identifiable reviewer data in any artifact (quotes should be anonymous / stripped as needed). |

---

## Success Criteria (Checklist)

- [ ] Reviews imported for ~8–12 weeks from the ChatGPT Play Store listing
- [ ] Reviews clustered into ≤5 themes
- [ ] One-page weekly pulse (≤250 words) with top 3 themes, 3 verbatim quotes, 3 action ideas
- [ ] Pulse published to Google Docs via MCP
- [ ] Draft email created in Gmail via MCP (self/alias), containing or linking to the pulse
- [ ] No PII in any deliverable; no ToS-violating scraping; MCP-first Docs/Gmail integration
