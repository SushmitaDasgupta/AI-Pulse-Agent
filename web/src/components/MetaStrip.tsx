import type { PulseData } from '../data/pulse'
import { Icon } from './Icon'

type MetaStripProps = {
  data: PulseData
  status: 'ready' | 'running'
}

export function MetaStrip({ data, status }: MetaStripProps) {
  return (
    <div className="flex w-full flex-wrap items-center justify-between gap-space-md rounded-xl bg-surface-container-lowest px-space-lg py-space-md shadow-sm">
      <div className="flex flex-wrap items-center gap-space-lg">
        <div className="flex items-center gap-space-xs text-sm text-on-surface-variant">
          <Icon name="calendar_today" className="text-[16px] text-primary" />
          <span className="font-medium text-on-surface">{data.window.start}</span>
          <span className="text-outline-variant">→</span>
          <span className="font-medium text-on-surface">{data.window.end}</span>
        </div>
        <div className="flex items-center gap-space-xs text-sm text-on-surface-variant">
          <Icon name="analytics" className="text-[16px] text-tertiary" />
          <span>Cleaned sample:</span>
          <span className="font-semibold text-on-surface">
            {data.cleanedReviews.toLocaleString()} reviews
          </span>
        </div>
        <div className="inline-flex items-center gap-space-xs rounded-full bg-surface-container px-space-sm py-0.5 text-[11px] font-semibold tracking-wide text-tertiary">
          <Icon name="short_text" className="text-[14px]" />
          <span>≤250 words · {data.wordCount}</span>
        </div>
        {status === 'ready' ? (
          <div className="inline-flex items-center gap-1.5 rounded-full bg-primary-fixed px-space-sm py-0.5 text-[11px] font-semibold text-primary">
            <span className="h-2 w-2 rounded-full bg-primary" />
            <span>Synthesized & Ready</span>
          </div>
        ) : (
          <div className="inline-flex items-center gap-1.5 rounded-full bg-secondary-fixed/60 px-space-sm py-0.5 text-[11px] font-semibold text-on-secondary-fixed-variant">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-secondary opacity-75" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-secondary" />
            </span>
            <span>Running</span>
          </div>
        )}
      </div>
      <a
        className="group inline-flex items-center gap-space-xs text-[13px] font-semibold text-primary transition-colors hover:text-primary-container"
        href={data.docUrl}
        target="_blank"
        rel="noreferrer"
      >
        <span>View rolling archive (Google Doc)</span>
        <Icon
          name="arrow_outward"
          className="text-[16px] transition-transform group-hover:translate-x-0.5"
        />
      </a>
    </div>
  )
}
