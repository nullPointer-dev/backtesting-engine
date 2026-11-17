export function LogoMark({ size = 28 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 28 28" aria-hidden="true">
      <rect width="28" height="28" rx="4" fill="var(--color-gain)" />
      <path
        d="M6 19l5-6 4 3 7-9"
        fill="none"
        stroke="var(--color-canvas)"
        strokeWidth="2.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

export function Logo() {
  return (
    <span className="inline-flex items-center gap-2.5">
      <LogoMark />
      <span className="text-lg font-bold tracking-[-0.01em]">Backtester</span>
    </span>
  )
}
