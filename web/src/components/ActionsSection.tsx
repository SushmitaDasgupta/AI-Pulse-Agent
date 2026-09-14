import type { Action } from '../data/pulse'
import { Icon } from './Icon'

type ActionsSectionProps = {
  actions: Action[]
}

export function ActionsSection({ actions }: ActionsSectionProps) {
  return (
    <section className="mt-space-sm flex w-full flex-col gap-space-md pb-space-sm">
      <div className="flex items-center justify-between gap-space-sm">
        <div className="flex items-center gap-space-sm">
          <span className="h-2.5 w-2.5 rounded-full bg-primary-container" />
          <h2 className="font-display text-xl font-bold tracking-tight text-on-surface">
            Recommended Actions for Product & Support
          </h2>
        </div>
        <div className="hidden items-center gap-space-xs text-[11px] font-semibold text-on-surface-variant sm:flex">
          <Icon name="verified" className="text-[15px] text-primary" />
          <span>AI synthesized triage playbook</span>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-space-md md:grid-cols-3">
        {actions.map((action) => (
          <div
            key={action.title}
            className="flex flex-col justify-between rounded-xl bg-surface-container-lowest p-space-lg shadow-sm transition-shadow hover:shadow-md"
          >
            <div>
              <div className="mb-space-sm flex items-center justify-between">
                <span className="rounded bg-primary/10 px-space-sm py-0.5 text-[11px] font-semibold text-primary">
                  {action.theme}
                </span>
                <Icon name={action.icon} className="text-[20px] text-primary" />
              </div>
              <h3 className="mt-space-xs font-display text-base font-bold tracking-tight text-on-surface">
                {action.title}
              </h3>
              <p className="mt-space-sm text-sm leading-relaxed text-on-surface-variant">
                {action.rationale}
              </p>
            </div>
            <div className="mt-space-md border-t border-surface-container pt-space-lg text-[11px] font-medium text-on-surface-variant">
              Grounded in theme signal · no invented wording
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}
