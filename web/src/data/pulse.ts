export type Theme = {
  label: string
  summary: string
  reviewCount: number
  frictionLabel: string
  volumeShare: string
}

export type Quote = {
  text: string
  theme: string
  rating: number
}

export type Action = {
  title: string
  rationale: string
  theme: string
  icon: string
}

export type PulseData = {
  product: string
  appId: string
  isoWeek: string
  window: { start: string; end: string }
  cleanedReviews: number
  wordCount: number
  generatedAtLabel: string
  docUrl: string
  topThemes: Theme[]
  quotes: Quote[]
  actions: Action[]
  markdown: string
}

/** Seeded from out/pulse.json — UI-only; no live backend. */
export const pulse: PulseData = {
  product: 'ChatGPT (Android)',
  appId: 'com.openai.chatgpt',
  isoWeek: '2026-W37',
  window: { start: '2026-08-26', end: '2026-09-09' },
  cleanedReviews: 9428,
  wordCount: 232,
  generatedAtLabel: '2026-09-11 04:09 UTC',
  docUrl:
    'https://docs.google.com/document/d/1GrxdD-fvsyLYHcmCgV0fRWLt3dqQoAfqrjS0MhcHYu0/edit',
  topThemes: [
    {
      label: 'Image & photo generation limits',
      summary:
        'Photo/image upload or generation caps, slow image creates, vision limits.',
      reviewCount: 1170,
      frictionLabel: 'Severe friction index',
      volumeShare: '12.4%',
    },
    {
      label: 'Paywall / limits / upgrade friction',
      summary:
        'Free-tier chat caps, Plus/Go/Pro upgrade nags, billing and subscription pain.',
      reviewCount: 555,
      frictionLabel: 'Conversion bottleneck',
      volumeShare: '5.9%',
    },
    {
      label: 'Answer quality / misunderstandings',
      summary:
        'Wrong answers, flip-flopping when corrected, not understanding the user.',
      reviewCount: 311,
      frictionLabel: 'Accuracy regression',
      volumeShare: '3.3%',
    },
  ],
  quotes: [
    {
      text: 'it is like the dumbest creature I have ever seen. one time I took a photo of my chemistry book and told it read and for every word',
      theme: 'Image & photo generation limits',
      rating: 1,
    },
    {
      text: 'the bot is good but you telling me that I can go and use Gemini and I dont have any problems I can keep chatting for as long',
      theme: 'Paywall / limits / upgrade friction',
      rating: 1,
    },
    {
      text: "it started lying to me. I'm trying to do a book because I'm dying of a disease I got this app because I was told it was the",
      theme: 'Answer quality / misunderstandings',
      rating: 1,
    },
  ],
  actions: [
    {
      title: 'Make image/photo quotas understandable and fair',
      rationale:
        'Users complain about limited photo generation/upload; explain caps and improve fallback messaging.',
      theme: 'Image & photo generation limits',
      icon: 'speed',
    },
    {
      title: 'Clarify free-tier limits before users hit the wall',
      rationale:
        'Reviews cite abrupt chat/photo caps and upgrade nags; surface remaining quota earlier.',
      theme: 'Paywall / limits / upgrade friction',
      icon: 'tune',
    },
    {
      title: 'Reduce confident-wrong answers and flip-flops',
      rationale:
        '1★ reviews describe incorrect answers that agree after correction; tighten grounding and correction UX.',
      theme: 'Answer quality / misunderstandings',
      icon: 'shield',
    },
  ],
  markdown: `# ChatGPT (Android) Play Pulse

**Window:** 2026-08-26 → 2026-09-09 · **Cleaned reviews:** 9,428

## Top themes
1. **Image & photo generation limits** (n=1170)
2. **Paywall / limits / upgrade friction** (n=555)
3. **Answer quality / misunderstandings** (n=311)

## Action ideas
1. Make image/photo quotas understandable and fair
2. Clarify free-tier limits before users hit the wall
3. Reduce confident-wrong answers and flip-flops

Google Doc: https://docs.google.com/document/d/1GrxdD-fvsyLYHcmCgV0fRWLt3dqQoAfqrjS0MhcHYu0/edit
`,
}

export const PIPELINE_STAGES = [
  'Acquire',
  'Normalize',
  'Scrub',
  'Theme',
  'Select',
  'Compose',
  'Validate',
  'Publish Doc',
  'Email',
] as const

function formatDayMonth(isoDate: string): string {
  const stamp = new Date(`${isoDate.slice(0, 10)}T00:00:00Z`)
  if (Number.isNaN(stamp.getTime())) return isoDate
  return stamp.toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'short',
    timeZone: 'UTC',
  })
}

function formatWindow(data: PulseData): string {
  const start = formatDayMonth(data.window.start)
  const end = formatDayMonth(data.window.end)
  const year = data.window.end.slice(0, 4)
  return `${start} → ${end} ${year}`
}

export function buildDefaultEmail(data: PulseData) {
  const themes = data.topThemes
    .map((t, i) => {
      const head = `${i + 1}. ${t.label} (n=${t.reviewCount.toLocaleString()})`
      return t.summary ? `${head}\n   ${t.summary}` : head
    })
    .join('\n')
  const actions = data.actions
    .map((a, i) => `${i + 1}. ${a.title}`)
    .join('\n')

  return {
    to: 'sushmitadasgupta7@gmail.com',
    subject: `ChatGPT Play Pulse — ${data.isoWeek}`,
    body: `${data.product} Play Pulse — ${data.isoWeek}

Weekly signal from Android Google Play reviews.
Window: ${formatWindow(data)} · ${data.cleanedReviews.toLocaleString()} cleaned reviews · ${data.wordCount} words

Top themes
${themes}

Suggested actions
${actions}

Read the full pulse (quotes + detail):
${data.docUrl}

—
Draft only — review in Gmail, then send when ready.
AI Review Pulsator`,
  }
}
