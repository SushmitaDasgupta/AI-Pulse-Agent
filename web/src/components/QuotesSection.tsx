import type { Quote } from '../data/pulse'
import { Icon } from './Icon'

type QuotesSectionProps = {
  quotes: Quote[]
}

export function QuotesSection({ quotes }: QuotesSectionProps) {
  return (
    <section className="mt-space-sm flex w-full flex-col gap-space-md">
      <div className="flex flex-col justify-between gap-space-xs sm:flex-row sm:items-baseline">
        <div className="flex flex-wrap items-center gap-space-sm">
          <span className="h-2.5 w-2.5 rounded-full bg-secondary" />
          <h2 className="font-display text-xl font-bold tracking-tight text-on-surface">
            Verbatim Voice of Customer
          </h2>
          <span className="text-sm text-on-surface-variant">
            · Anonymous Play Store excerpts
          </span>
        </div>
        <span className="text-[11px] font-semibold text-on-surface-variant">
          Zero PII retained · Device IDs scrubbed
        </span>
      </div>

      <div className="grid grid-cols-1 gap-space-md md:grid-cols-3">
        {quotes.map((quote) => (
          <div
            key={quote.text}
            className="relative flex flex-col justify-between overflow-hidden rounded-xl bg-surface-container-lowest p-space-lg shadow-sm"
          >
            <div className="pointer-events-none absolute right-0 top-0 select-none translate-x-3 -translate-y-3 font-display text-6xl text-surface-container">
              “
            </div>
            <div>
              <div className="mb-space-md flex items-center justify-between">
                <div className="inline-flex items-center gap-0.5 rounded-full bg-error-container px-space-sm py-0.5 text-[11px] font-bold text-on-error-container">
                  <Icon name="star" className="text-[14px]" filled />
                  <span>{quote.rating.toFixed(1)}</span>
                </div>
              </div>
              <div className="my-space-sm border-l-2 border-secondary pl-space-md">
                <p className="text-sm italic leading-relaxed text-on-surface">
                  “{quote.text}”
                </p>
              </div>
            </div>
            <div className="flex items-center gap-space-xs pt-space-md text-[11px] font-medium text-on-surface-variant">
              <Icon name="label" className="text-[15px] text-secondary" />
              <span>Theme: {quote.theme}</span>
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}
