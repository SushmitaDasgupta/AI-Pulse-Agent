---
name: Executive Pulse
colors:
  surface: '#fcf9f4'
  surface-dim: '#dcdad5'
  surface-bright: '#fcf9f4'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f6f3ee'
  surface-container: '#f0ede9'
  surface-container-high: '#ebe8e3'
  surface-container-highest: '#e5e2dd'
  on-surface: '#1c1c19'
  on-surface-variant: '#3f4946'
  inverse-surface: '#31302d'
  inverse-on-surface: '#f3f0eb'
  outline: '#6f7976'
  outline-variant: '#bec9c5'
  surface-tint: '#0e6a5b'
  primary: '#005145'
  on-primary: '#ffffff'
  primary-container: '#0f6b5c'
  on-primary-container: '#99e8d5'
  inverse-primary: '#86d5c3'
  secondary: '#9a442d'
  on-secondary: '#ffffff'
  secondary-container: '#fc9174'
  on-secondary-container: '#742814'
  tertiary: '#4c4642'
  on-tertiary: '#ffffff'
  tertiary-container: '#645e59'
  on-tertiary-container: '#e1d8d2'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#a2f2de'
  primary-fixed-dim: '#86d5c3'
  on-primary-fixed: '#00201a'
  on-primary-fixed-variant: '#005144'
  secondary-fixed: '#ffdbd2'
  secondary-fixed-dim: '#ffb4a1'
  on-secondary-fixed: '#3c0800'
  on-secondary-fixed-variant: '#7c2e19'
  tertiary-fixed: '#eae1da'
  tertiary-fixed-dim: '#cec5bf'
  on-tertiary-fixed: '#1f1b17'
  on-tertiary-fixed-variant: '#4b4641'
  background: '#fcf9f4'
  on-background: '#1c1c19'
  surface-variant: '#e5e2dd'
typography:
  display-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 36px
    fontWeight: '700'
    lineHeight: 44px
    letterSpacing: -0.03em
  display-lg-mobile:
    fontFamily: Plus Jakarta Sans
    fontSize: 28px
    fontWeight: '700'
    lineHeight: 36px
    letterSpacing: -0.025em
  headline-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
    letterSpacing: -0.015em
  headline-sm:
    fontFamily: Plus Jakarta Sans
    fontSize: 16px
    fontWeight: '600'
    lineHeight: 24px
    letterSpacing: -0.01em
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 26px
    letterSpacing: -0.011em
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 22px
    letterSpacing: -0.006em
  body-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 18px
    letterSpacing: 0em
  label-md:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0.01em
  label-sm:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '600'
    lineHeight: 14px
    letterSpacing: 0.04em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  gutter: 1.5rem
  gutter-mobile: 1rem
  margin: 2.5rem
  margin-mobile: 1rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2.5rem
---

## Brand & Style

This design system embodies the rigor of high-grade investigative journalism paired with the precision of an executive decision-support system. It transforms high-velocity, chaotic app store feedback into authoritative intelligence briefings.

### Personality & Emotional Tenor
- **Calm Authority:** Eliminates triage panic through quiet confidence, measured contrast, and editorial discipline.
- **Analytical Clarity:** Replaces raw sentiment noise with structural synthesis, giving product and executive leadership instant clarity.
- **Tactile Dignity:** Evokes high-end printed business periodicals, broadsheet digests, and institutional paper stock.

### Design Movement
The visual architecture follows an **Editorial Minimalist** aesthetic. It relies on architectural typography, crisp single-pixel hairpins, structured horizontal datelines, and deliberate white space. It completely eschews loud gradients, heavy blurs, and neon accents in favor of a warm, paper-like clarity.

## Colors

The palette references classic editorial printing: newsprint warm neutrals anchored by a deep ink-like forest teal and highlighted with intentional terracotta/coral accents.

### Core Roles
- **Canvas Base (`#F7F4EF`):** Soft, warm off-white that prevents screen fatigue during deep review analysis and mimics uncoated matte paper.
- **Surface Cards (`#FFFFFF`):** Crisp pure white reserved for data containers, intelligence blocks, and discrete visual groupings.
- **Primary Ink (`#0F6B5C`):** Deep, balanced teal used for primary actions, selected navigation states, interactive links, and prominent metrics. Hover state shifts to `#0B5448`.
- **Editorial Accent (`#E07A5F`):** Warm terracotta coral reserved for urgency calls, velocity spikes, top-rank badges, and critical shifts in user sentiment.

### Functional Roles
- **Text Primary (`#1C1917`):** Stone-900 warm black for maximum contrast and readability without digital harshness.
- **Text Muted (`#78716C`):** Warm charcoal for secondary metadata, timestamps, author IDs, and context metrics.
- **Border / Divider (`#E7E5E4`):** Soft stone hairline dividers that structure the page without visual clutter.
- **Feedback Accents:** Success (`#15803D`), Progress/Caution (`#B45309`), Critical/Friction (`#B91C1C`).

## Typography

The type system blends the geometric authority of **Plus Jakarta Sans** for section titles and metrics with the functional clarity of **Inter** for sustained review reading and metadata analysis.

### Editorial Hierarchy Rules
- Section headings like "This week's pulse" use `headline-lg` or `headline-md` set in Plus Jakarta Sans with tight negative letter tracking (`-0.02em`), emulating modern broadsheet titles.
- Raw Play Store reviews, AI synthesis summaries, and impact briefs are set in `body-md` and `body-lg` using Inter with generous line height for effortless long-form scanning.
- Metadata categories, tag indicators, and date indicators utilize `label-sm` in uppercase or strong medium weights to punctuate body sections.

## Layout & Spacing

The layout operates on a fixed-fluid editorial grid that prioritizes structural hierarchy and clean reading rails.

### Grid Anatomy
- **Desktop (>= 1280px):** 12-column grid capped at a maximum width of 1440px with a 40px (`margin`) outer canvas and 24px (`gutter`) inter-column spacing. Layout structures follow an 8-column primary dossier area and a 4-column executive pulse rail.
- **Tablet (768px - 1279px):** 8-column layout with 24px margin and 16px gutter; the secondary sidebar docks beneath the summary view or stacks above individual reviews.
- **Mobile (< 768px):** Single-column stacked stream with 16px (`margin-mobile`) outer padding and 12px card gaps.

### Spacing Cadence
Component internals use strict standard increments:
- `space-xs` (4px) and `space-sm` (8px) for micro-alignments, tag internal padding, and badge anchors.
- `space-md` (16px) for item separation inside cards and form rows.
- `space-lg` (24px) for card interior padding and module headers.
- `space-xl` (40px) for separating weekly editorial modules and major pulse dossiers.

## Elevation & Depth

Visual depth avoids excessive drop shadows, relying instead on clean paper layering and structural line work.

### Layering Principles
- **Base Canvas:** `#F7F4EF` provides a grounded, physical backdrop.
- **Cards & Sheets:** Pure white (`#FFFFFF`) surfaces rise above the base through crisp 1px borders (`#E7E5E4`) rather than dramatic shadows.
- **Ambient Floor:** Interactive cards and active briefing items use a faint, warm ambient shadow: `0 1px 3px rgba(28, 25, 23, 0.04), 0 6px 16px -4px rgba(28, 25, 23, 0.03)`.
- **Flyouts & Dropdowns:** Elevated controls feature an opacity-restrained shadow: `0 12px 28px -4px rgba(28, 25, 23, 0.08), 0 0 0 1px rgba(231, 229, 228, 0.8)`.

## Shapes

The design system uses a restrained corner radius level (`1` / Soft) to preserve an editorial and structured feel.

### Geometric Application
- **Standard UI Cards & Panels:** `0.25rem` (4px) or `0.5rem` (8px) for `rounded-lg`, keeping panels sharp and rectangular like index cards and report pages.
- **Badges, Status Tags, Chips:** `0.25rem` (4px) for crisp categorization; pills are strictly avoided except for numeric notification counts.
- **Action Buttons & Inputs:** `0.375rem` (6px) balancing tactile usability with professional architecture.

## Components

### Buttons
- **Primary:** Background `#0F6B5C`, text `#FFFFFF`, border none, hover `#0B5448`. Focused with a 2px offset ring in `#0F6B5C`.
- **Secondary / Outline:** Background `#FFFFFF`, text `#1C1917`, border 1px solid `#E7E5E4`, hover background `#F7F4EF`.
- **Accent / Coral:** Background `#E07A5F`, text `#FFFFFF`, hover background `#CD664B`. Used exclusively for critical briefing triggers or urgent filters.

### Chips & Pulse Badges
- **Editorial Category Tags:** Background `#F7F4EF`, border 1px solid `#E7E5E4`, text `#78716C`, font size `11px`, bold tracking.
- **Coral Rank Badges:** Background `rgba(224, 122, 95, 0.12)`, border 1px solid `rgba(224, 122, 95, 0.25)`, text `#E07A5F`, font weight `600`.
- **Teal Active Filter:** Background `rgba(15, 107, 92, 0.1)`, border 1px solid `#0F6B5C`, text `#0F6B5C`.

### Cards & Intelligence Dossiers
- **Pulse Card:** Pure white background, 1px solid `#E7E5E4`, `space-lg` padding, with an optional 3px left-accent border in `#0F6B5C` for verified high-impact items or `#E07A5F` for recurring regressions.
- **Review Feed Card:** Subtly nested layout containing star rating, build number, sentiment shift vector, and the raw review quote accompanied by the AI-condensed thematic takeaway.

### Input Fields & Selectors
- Background `#FFFFFF`, border 1px solid `#E7E5E4`, placeholder `#78716C`, text `#1C1917`, height 40px, padding `0 12px`. Active focus shifts border to `#0F6B5C` with a faint `0 0 0 1px #0F6B5C` halo.

### Checkboxes & Segmented Controls
- Checkbox borders use `#78716C` at rest, transitioning to `#0F6B5C` fill with a white checkmark on selection.
- Segmented time pickers (e.g., "7D", "Weekly Pulse", "30D") feature a `#E7E5E4` track with a white raised segment indicator and muted text transitioning to `#1C1917`.

### Specialized Domain Components
- **Executive Digest Header:** A newspaper-style masthead module incorporating issue date, aggregate rating delta, volume velocity, and primary sentiment vectors.
- **Quote Pullout Block:** Used for verbatim customer quotes; set with an indented 2px left border in `#E07A5F` and italicized `body-lg` text in `#1C1917`.