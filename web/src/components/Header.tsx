import { Icon } from './Icon'

type HeaderProps = {
  onRun: () => void
  onSendEmail: () => void
  running: boolean
}

export function Header({ onRun, onSendEmail, running }: HeaderProps) {
  return (
    <header className="fixed top-0 z-40 w-full border-b border-surface-container-highest bg-surface/90 backdrop-blur-md">
      <div className="mx-auto flex h-20 max-w-6xl items-center justify-between px-gutter">
        <div className="flex items-center gap-space-md">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary-container text-on-primary shadow-sm">
            <Icon name="monitoring" className="text-[20px]" />
          </div>
          <div className="flex flex-col">
            <span className="font-display text-xl font-bold tracking-tight text-on-surface">
              AI Review Pulsator
            </span>
            <span className="text-xs font-medium text-on-surface-variant">
              ChatGPT (Android) · Google Play
            </span>
          </div>
        </div>

        <nav className="hidden items-center gap-space-lg lg:flex" aria-label="Primary">
          <span className="text-sm font-semibold text-primary">Weekly Pulse</span>
        </nav>

        <div className="flex items-center gap-space-sm">
          <button
            type="button"
            onClick={onRun}
            disabled={running}
            className="inline-flex items-center gap-space-xs rounded-xl border border-surface-container-highest bg-surface-container-lowest px-space-md py-space-sm text-[13px] font-medium text-on-surface transition-colors hover:bg-surface-container-low disabled:cursor-not-allowed disabled:opacity-60"
          >
            <Icon name="refresh" className="text-[18px] text-tertiary" />
            <span className="hidden sm:inline">
              {running ? 'Running…' : 'Run weekly pulse'}
            </span>
          </button>
          <button
            type="button"
            onClick={onSendEmail}
            disabled={running}
            className="inline-flex items-center gap-space-xs rounded-xl bg-primary-container px-space-md py-space-sm text-[13px] font-semibold text-on-primary transition-colors hover:bg-primary disabled:cursor-not-allowed disabled:opacity-60"
          >
            <Icon name="mail" className="text-[18px]" />
            <span className="hidden sm:inline">Send email</span>
          </button>
        </div>
      </div>
    </header>
  )
}
