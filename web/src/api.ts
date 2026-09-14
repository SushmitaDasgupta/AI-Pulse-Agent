/** Browser client for the Railway pulse service. */

const DEFAULT_API_BASE = 'https://ai-pulse-agent-production.up.railway.app'

export function apiBaseUrl(): string {
  const raw = (import.meta.env.VITE_API_BASE_URL as string | undefined) || DEFAULT_API_BASE
  return raw.replace(/\/$/, '')
}

export type DeliverResult = {
  status: string
  document_id?: string
  doc_url?: string
  draft_id?: string
  to?: string
  subject?: string
  error?: string
}

async function parseJson(response: Response): Promise<Record<string, unknown>> {
  const text = await response.text()
  if (!text) return {}
  try {
    return JSON.parse(text) as Record<string, unknown>
  } catch {
    return { error: text.slice(0, 300) }
  }
}

export async function startWeeklyRun(): Promise<void> {
  const response = await fetch(`${apiBaseUrl()}/run`, { method: 'POST' })
  if (!response.ok && response.status !== 202) {
    const body = await parseJson(response)
    throw new Error(String(body.error || `Run failed (${response.status})`))
  }
}

export async function deliverPulse(input: {
  to: string
  subject: string
  body: string
}): Promise<DeliverResult> {
  const response = await fetch(`${apiBaseUrl()}/deliver`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  })
  const body = (await parseJson(response)) as DeliverResult
  if (!response.ok) {
    throw new Error(String(body.error || `Deliver failed (${response.status})`))
  }
  return body
}
