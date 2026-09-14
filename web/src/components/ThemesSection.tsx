import type { Theme } from '../data/pulse'
import { Icon } from './Icon'

const accentBars = ['bg-primary', 'bg-tertiary-container', 'bg-outline'] as const
const frictionIcons = ['priority_high', 'hourglass_bottom', 'psychology_alt'] as const

type ThemesSectionProps = {
  themes: Theme[]
  totalReviews: number
}

export function ThemesSection({ themes, totalReviews }: ThemesSectionProps) {
  const covered = themes.reduce((sum, t) => sum + t.reviewCount, 0)
  const share = totalReviews > 0 ? ((covered / totalReviews) * 100).toFixed(1) : '0'

  return (
    <section className="mt-space-xs flex w-full flex-col gap-space-md">
      <div className="flex items-center justify-between gap-space-sm">
        <div className="flex items-center gap-space-sm">
          <span className="h-2.5 w-2.5 rounded-full bg-primary" />
          <h2 className="font-display text-xl font-bold tracking-tight text-on-surface">
            Top Themes
          </h2>
          <span className="rounded bg-surface-container px-space-sm py-0.5 text-[11px] font-semibold text-tertiary">
            Triaged by volume
          </span>
        </div>
        <span className="hidden text-[11px] font-semibold text-on-surface-variant sm:inline">
          Representing {share}% of cleaned reviews in top 3
        </span>
      </div>

      <div className="grid grid-cols-1 gap-space-md md:grid-cols-3">
        {themes.map((theme, index) => (
          <article
            key={theme.label}
            className="group relative flex flex-col justify-between overflow-hidden rounded-xl bg-surface-container-lowest p-space-lg shadow-sm transition-shadow hover:shadow-md"
          >
            <div
              className={`absolute bottom-0 left-0 top-0 w-1.5 rounded-l-xl ${accentBars[index] ?? 'bg-outline'}`}
            />
            <div className="flex flex-col pl-space-xs">
              <div className="mb-space-sm flex items-center justify-between">
                <span
                  className={`inline-flex h-6 w-6 items-center justify-center rounded-full text-[11px] font-bold shadow-sm ${
                    index === 0
                      ? 'bg-secondary-container text-on-secondary-container'
                      : 'bg-surface-container-highest text-tertiary'
                  }`}
                >
                  #{index + 1}
                </span>
                <span
                  className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${
                    index === 0
                      ? 'bg-secondary-fixed/50 text-secondary'
                      : 'bg-surface-container text-on-surface-variant'
                  }`}
                >
                  n={theme.reviewCount.toLocaleString()} reviews
                </span>
              </div>
              <h3 className="mt-space-xs font-display text-base font-bold tracking-tight text-on-surface">
                {theme.label}
              </h3>
              <p className="mt-space-sm text-sm leading-relaxed text-on-surface-variant">
                {theme.summary}
              </p>
            </div>
            <div className="mt-space-md flex items-center justify-between border-t border-surface-container pl-space-xs pt-space-lg">
              <div
                className={`flex items-center gap-space-xs text-[11px] font-medium ${
                  index === 0 ? 'text-secondary' : 'text-on-surface-variant'
                }`}
              >
                <Icon
                  name={frictionIcons[index] ?? 'label'}
                  className={`text-[16px] ${index === 0 ? '' : 'text-tertiary'}`}
                />
                <span>{theme.frictionLabel}</span>
              </div>
              <span className="font-mono text-[11px] text-tertiary">
                Vol: {theme.volumeShare}
              </span>
            </div>
          </article>
        ))}
      </div>
    </section>
  )
}
