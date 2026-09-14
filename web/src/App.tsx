import { useCallback, useEffect, useState } from 'react'
import { ActionsSection } from './components/ActionsSection'
import { ArchiveBar, Footer } from './components/ArchiveBar'
import { Header } from './components/Header'
import { MetaStrip } from './components/MetaStrip'
import { PipelineOverlay } from './components/PipelineOverlay'
import { QuotesSection } from './components/QuotesSection'
import { SendEmailModal } from './components/SendEmailModal'
import { ThemesSection } from './components/ThemesSection'
import { Toast } from './components/Toast'
import { PIPELINE_STAGES, pulse } from './data/pulse'
import { Icon } from './components/Icon'

export default function App() {
  const [emailOpen, setEmailOpen] = useState(false)
  const [running, setRunning] = useState(false)
  const [stageIndex, setStageIndex] = useState(0)
  const [toast, setToast] = useState<{ message: string; detail?: string } | null>(null)

  useEffect(() => {
    if (!running) return
    if (stageIndex >= PIPELINE_STAGES.length) {
      const timer = window.setTimeout(() => {
        setRunning(false)
        setStageIndex(0)
        setToast({
          message: 'Weekly pulse ready',
          detail: 'Simulated pipeline finished — seed data unchanged (UI-only).',
        })
      }, 500)
      return () => window.clearTimeout(timer)
    }
    const timer = window.setTimeout(() => {
      setStageIndex((current) => current + 1)
    }, 420)
    return () => window.clearTimeout(timer)
  }, [running, stageIndex])

  useEffect(() => {
    if (!toast) return
    const timer = window.setTimeout(() => setToast(null), 4200)
    return () => window.clearTimeout(timer)
  }, [toast])

  const startRun = useCallback(() => {
    if (running) return
    setEmailOpen(false)
    setStageIndex(0)
    setRunning(true)
  }, [running])

  return (
    <div className="min-h-svh bg-surface text-on-surface antialiased">
      <Header
        onRun={startRun}
        onSendEmail={() => setEmailOpen(true)}
        running={running}
      />

      <PipelineOverlay
        open={running}
        activeIndex={Math.min(stageIndex, PIPELINE_STAGES.length - 1)}
        reviewCount={pulse.cleanedReviews}
        isoWeek={pulse.isoWeek}
      />

      <main
        className={`w-full bg-surface pt-20 transition-[filter,opacity] duration-300 ${
          running ? 'pointer-events-none opacity-45 blur-[2px]' : ''
        }`}
      >
        <div className="mx-auto flex max-w-6xl flex-col gap-space-lg px-gutter py-space-lg">
          <MetaStrip data={pulse} status={running ? 'running' : 'ready'} />

          <div className="flex w-full flex-col justify-between gap-space-md pt-space-xs md:flex-row md:items-end">
            <div className="max-w-2xl">
              <div className="mb-space-xs inline-flex items-center gap-space-xs text-[11px] font-semibold uppercase tracking-wider text-primary">
                <Icon name="electric_bolt" className="text-[15px]" />
                <span>Weekly Play Pulse · {pulse.isoWeek}</span>
              </div>
              <h1 className="font-display text-3xl font-bold tracking-tight text-on-surface md:text-4xl md:leading-[1.15]">
                This week’s pulse
              </h1>
              <p className="mt-space-xs text-sm leading-relaxed text-on-surface-variant">
                Weekly synthesized intelligence from{' '}
                {pulse.cleanedReviews.toLocaleString()} cleaned Android Google Play
                reviews for{' '}
                <span className="rounded bg-surface-container px-1 font-mono text-tertiary">
                  {pulse.appId}
                </span>
                .
              </p>
            </div>
          </div>

          <ThemesSection themes={pulse.topThemes} totalReviews={pulse.cleanedReviews} />
          <QuotesSection quotes={pulse.quotes} />
          <ActionsSection actions={pulse.actions} />
          <ArchiveBar data={pulse} />
        </div>
      </main>

      <Footer data={pulse} />

      <SendEmailModal
        open={emailOpen}
        data={pulse}
        onClose={() => setEmailOpen(false)}
        onSent={(to) =>
          setToast({
            message: `Pulse emailed to ${to}`,
            detail: 'UI simulation — message not sent via Gmail MCP.',
          })
        }
      />

      {toast ? (
        <Toast
          message={toast.message}
          detail={toast.detail}
          onDismiss={() => setToast(null)}
        />
      ) : null}
    </div>
  )
}
