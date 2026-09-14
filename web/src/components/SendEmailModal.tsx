import { useEffect, useId, useState, type FormEvent } from 'react'
import { buildDefaultEmail, type PulseData } from '../data/pulse'
import { Icon } from './Icon'

type SendEmailModalProps = {
  open: boolean
  data: PulseData
  onClose: () => void
  onSent: (to: string) => void
}

export function SendEmailModal({ open, data, onClose, onSent }: SendEmailModalProps) {
  const titleId = useId()
  const defaults = buildDefaultEmail(data)
  const [to, setTo] = useState(defaults.to)
  const [subject, setSubject] = useState(defaults.subject)
  const [body, setBody] = useState(defaults.body)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!open) return
    const next = buildDefaultEmail(data)
    setTo(next.to)
    setSubject(next.subject)
    setBody(next.body)
    setError(null)
    setSending(false)
  }, [open, data])

  useEffect(() => {
    if (!open) return
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open, onClose])

  if (!open) return null

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    if (!to.trim() || !subject.trim() || !body.trim()) {
      setError('To, subject, and body are required.')
      return
    }
    setSending(true)
    setError(null)
    // UI-only: simulate send latency
    await new Promise((resolve) => setTimeout(resolve, 650))
    setSending(false)
    onSent(to.trim())
    onClose()
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-on-surface/40 p-space-md backdrop-blur-sm"
      role="presentation"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className="flex w-full max-w-xl flex-col overflow-hidden rounded-xl bg-surface-container-lowest shadow-xl"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-start justify-between bg-surface-container-low p-space-lg">
          <div className="flex flex-col gap-space-xs pr-space-md">
            <div className="mb-1 flex items-center gap-space-xs">
              <span className="rounded bg-primary/10 px-space-xs py-0.5 text-[11px] font-semibold text-primary">
                Executive Dispatch
              </span>
              <span className="text-sm text-tertiary">· {data.isoWeek}</span>
            </div>
            <h2 id={titleId} className="font-display text-2xl font-semibold tracking-tight text-on-surface">
              Send this week’s pulse
            </h2>
            <p className="text-sm text-on-surface-variant">
              Dispatch the briefing directly to your inbox or team distribution list.
            </p>
          </div>
          <button
            type="button"
            aria-label="Close dialog"
            onClick={onClose}
            className="-mr-1 -mt-1 flex h-8 w-8 items-center justify-center rounded-lg text-tertiary transition-colors hover:bg-surface-container hover:text-on-surface"
          >
            <Icon name="close" className="text-[20px]" />
          </button>
        </div>

        <form className="flex flex-col gap-space-md bg-surface-container-lowest p-space-lg" onSubmit={handleSubmit}>
          <div className="flex flex-col gap-space-xs">
            <div className="flex items-center justify-between">
              <label className="text-[13px] font-semibold text-on-surface" htmlFor="email-to">
                To
              </label>
              <span className="text-xs text-tertiary">Recipients (comma separated)</span>
            </div>
            <div className="relative flex items-center">
              <span className="pointer-events-none absolute left-3 flex items-center text-tertiary">
                <Icon name="alternate_email" className="text-[18px]" />
              </span>
              <input
                id="email-to"
                className="h-10 w-full rounded-xl bg-surface-container-low pl-9 pr-3 text-sm text-on-surface transition-all focus:bg-surface-container-lowest focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-1"
                value={to}
                onChange={(e) => setTo(e.target.value)}
              />
            </div>
          </div>

          <div className="flex flex-col gap-space-xs">
            <label className="text-[13px] font-semibold text-on-surface" htmlFor="email-subject">
              Subject
            </label>
            <div className="relative flex items-center">
              <span className="pointer-events-none absolute left-3 flex items-center text-tertiary">
                <Icon name="subject" className="text-[18px]" />
              </span>
              <input
                id="email-subject"
                className="h-10 w-full rounded-xl bg-surface-container-low pl-9 pr-3 text-sm text-on-surface transition-all focus:bg-surface-container-lowest focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-1"
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
              />
            </div>
          </div>

          <div className="flex flex-col gap-space-xs">
            <div className="flex items-center justify-between">
              <label className="text-[13px] font-semibold text-on-surface" htmlFor="email-body">
                Body
              </label>
              <span className="text-[11px] font-semibold uppercase tracking-wider text-tertiary">
                Markdown supported
              </span>
            </div>
            <textarea
              id="email-body"
              rows={8}
              className="w-full resize-y rounded-xl bg-surface-container-low p-space-md font-mono text-xs leading-relaxed text-on-surface transition-all focus:bg-surface-container-lowest focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-1"
              value={body}
              onChange={(e) => setBody(e.target.value)}
            />
          </div>

          {error ? (
            <p className="rounded-lg bg-error-container px-space-sm py-space-sm text-sm text-on-error-container">
              {error}
            </p>
          ) : null}

          <div className="flex items-center justify-end gap-space-sm pt-space-sm">
            <button
              type="button"
              onClick={onClose}
              className="rounded-xl bg-surface-container px-space-md py-space-sm text-[13px] font-medium text-tertiary transition-colors hover:bg-surface-container-high hover:text-on-surface"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={sending}
              className="inline-flex items-center gap-space-xs rounded-xl bg-primary-container px-space-lg py-space-sm text-[13px] font-semibold text-on-primary shadow-sm transition-colors hover:bg-primary disabled:opacity-70"
            >
              <Icon name="send" className="text-[18px]" />
              <span>{sending ? 'Sending…' : 'Send now'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
