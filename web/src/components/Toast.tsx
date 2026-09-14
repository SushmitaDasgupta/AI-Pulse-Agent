import { Icon } from './Icon'

type ToastProps = {
  message: string
  detail?: string
  onDismiss: () => void
}

export function Toast({ message, detail, onDismiss }: ToastProps) {
  return (
    <div
      className="fixed right-8 top-24 z-[60] flex items-center gap-space-sm rounded-xl px-space-md py-space-sm text-white shadow-lg"
      style={{ backgroundColor: '#15803D' }}
      role="status"
    >
      <div className="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-white/20">
        <Icon name="check" className="text-[16px] text-white" />
      </div>
      <div className="flex flex-col">
        <span className="text-[13px] font-semibold text-white">{message}</span>
        {detail ? <span className="text-xs text-white/80">{detail}</span> : null}
      </div>
      <button
        type="button"
        aria-label="Dismiss toast"
        onClick={onDismiss}
        className="ml-space-sm flex items-center text-white/70 transition-colors hover:text-white"
      >
        <Icon name="close" className="text-[16px]" />
      </button>
    </div>
  )
}
