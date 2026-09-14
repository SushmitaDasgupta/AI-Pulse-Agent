import type { PulseData } from '../data/pulse'
import { Icon } from './Icon'

type ArchiveBarProps = {
  data: PulseData
}

export function ArchiveBar({ data }: ArchiveBarProps) {
  return (
    <div
      id="archive"
      className="flex w-full flex-col items-center justify-between gap-space-sm rounded-xl bg-surface-container-low px-space-lg py-space-md shadow-sm sm:flex-row"
    >
      <div className="flex items-center gap-space-md">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-surface-container-lowest text-primary shadow-sm">
          <Icon name="description" className="text-[20px]" />
        </div>
        <div className="flex flex-col">
          <div className="flex flex-wrap items-center gap-space-xs">
            <span className="font-display text-base font-bold text-on-surface">
              Published to Google Doc
            </span>
            <span className="text-tertiary">·</span>
            <a
              className="inline-flex items-center gap-0.5 text-[13px] font-semibold text-primary transition-colors hover:text-primary-container"
              href={data.docUrl}
              target="_blank"
              rel="noreferrer"
            >
              Open Doc → (rolling archive)
            </a>
          </div>
          <span className="text-xs text-on-surface-variant">
            Weekly pulse appended to the rolling executive ledger
          </span>
        </div>
      </div>
      <div className="flex items-center gap-space-xs rounded-lg bg-surface-container-lowest px-space-md py-1.5 font-mono text-[11px] text-on-surface-variant shadow-sm">
        <Icon name="update" className="text-[15px] text-tertiary" />
        <span>Last generated: {data.generatedAtLabel}</span>
      </div>
    </div>
  )
}

export function Footer({ data }: ArchiveBarProps) {
  return (
    <footer className="w-full border-t border-surface-container-highest bg-surface-container-lowest py-space-md">
      <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-space-xs px-gutter text-sm text-on-surface-variant sm:flex-row">
        <div className="flex items-center gap-space-sm">
          <span className="font-medium text-on-surface">Published to Google Doc</span>
          <span className="text-outline-variant">·</span>
          <a
            className="inline-flex items-center font-semibold text-primary transition-colors hover:text-primary-container"
            href={data.docUrl}
            target="_blank"
            rel="noreferrer"
          >
            Open Doc →
          </a>
        </div>
        <div className="flex items-center gap-space-xs">
          <Icon name="schedule" className="text-[14px] text-tertiary" />
          <span>Last generated: {data.generatedAtLabel}</span>
        </div>
      </div>
    </footer>
  )
}
