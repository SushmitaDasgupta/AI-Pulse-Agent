import { PIPELINE_STAGES } from '../data/pulse'
import { Icon } from './Icon'

type PipelineOverlayProps = {
  open: boolean
  activeIndex: number
  reviewCount: number
  isoWeek: string
}

export function PipelineOverlay({
  open,
  activeIndex,
  reviewCount,
  isoWeek,
}: PipelineOverlayProps) {
  if (!open) return null

  const progress = Math.min(
    100,
    Math.round(((activeIndex + 0.35) / PIPELINE_STAGES.length) * 100),
  )
  const activeLabel = PIPELINE_STAGES[Math.min(activeIndex, PIPELINE_STAGES.length - 1)]

  return (
    <div className="pointer-events-none fixed inset-x-0 top-20 z-30 px-gutter">
      <div className="pointer-events-auto mx-auto max-w-6xl overflow-hidden rounded-xl bg-surface-container-lowest p-space-lg shadow-lg ring-1 ring-hairline">
        <div className="relative z-10 flex flex-col gap-space-lg">
          <div className="flex flex-col justify-between gap-space-sm lg:flex-row lg:items-center">
            <div>
              <div className="mb-space-xs flex items-center gap-space-xs text-[11px] font-semibold uppercase tracking-wider text-primary">
                <Icon name="auto_awesome" className="text-[14px]" />
                <span>Active Editorial Pipeline</span>
              </div>
              <h2 className="font-display text-2xl font-semibold tracking-tight text-on-surface">
                Running Weekly Pulse Pipeline ({isoWeek})
              </h2>
            </div>
            <div className="flex items-center gap-space-sm self-start rounded-lg bg-surface-container-low px-space-md py-space-xs lg:self-auto">
              <Icon name="dataset" className="text-[20px] text-primary" />
              <span className="text-sm text-on-surface">
                Synthesizing{' '}
                <strong className="font-semibold">
                  {reviewCount.toLocaleString()} reviews
                </strong>
              </span>
            </div>
          </div>

          <div className="flex flex-col gap-space-xs">
            <div className="flex items-center justify-between text-[13px] font-medium">
              <span className="text-on-surface-variant">Pipeline Completion</span>
              <span className="font-semibold text-primary">{progress}%</span>
            </div>
            <div className="h-2.5 w-full overflow-hidden rounded-full bg-surface-container">
              <div
                className="h-full rounded-full bg-primary-container transition-all duration-700 ease-out"
                style={{ width: `${progress}%` }}
              />
            </div>
            <div className="flex items-center justify-between pt-space-xs text-xs text-on-surface-variant">
              <span>In-flight phase: {activeLabel}</span>
              <span className="italic text-tertiary">UI simulation · no backend call</span>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-space-xs pt-space-xs sm:grid-cols-3 md:grid-cols-5 lg:grid-cols-9">
            {PIPELINE_STAGES.map((stage, index) => {
              const done = index < activeIndex
              const active = index === activeIndex
              return (
                <div
                  key={stage}
                  className={`flex items-center gap-space-xs rounded-lg px-space-sm py-2 text-[11px] font-medium ${
                    active
                      ? 'animate-pulse bg-primary text-on-primary shadow-sm'
                      : done
                        ? 'bg-surface-container text-on-surface'
                        : 'bg-surface-container-low text-tertiary opacity-60'
                  }`}
                >
                  <Icon
                    name={active ? 'autorenew' : done ? 'check_circle' : 'radio_button_unchecked'}
                    className={`text-[15px] ${active ? 'text-primary-fixed' : done ? 'text-primary' : ''}`}
                    filled={done}
                  />
                  <span className={active ? 'font-semibold tracking-wide' : ''}>
                    {index + 1}. {stage}
                  </span>
                </div>
              )
            })}
          </div>
        </div>
      </div>
    </div>
  )
}
