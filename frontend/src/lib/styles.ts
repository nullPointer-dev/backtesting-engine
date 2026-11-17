// Class recipes shared by components (kept out of component files for fast refresh).

export type ButtonVariant = 'primary' | 'secondary' | 'accent' | 'danger' | 'dashed'

const buttonVariants: Record<ButtonVariant, string> = {
  primary: 'bg-ink text-canvas hover:bg-white',
  secondary: 'border border-line-strong bg-panel text-ink hover:border-ink',
  accent: 'bg-gain text-canvas hover:brightness-110',
  danger: 'border border-loss bg-loss text-canvas hover:brightness-110',
  dashed: 'border border-dashed border-line-strong bg-transparent text-muted hover:border-ink hover:text-ink',
}

const buttonSizes = {
  md: 'h-11 px-5 text-sm',
  sm: 'h-10 px-3.5 text-[13px]',
  xs: 'h-9 px-3.5 text-xs',
}

export function buttonClass(variant: ButtonVariant = 'primary', size: keyof typeof buttonSizes = 'md', extra = '') {
  return (
    'press inline-flex cursor-pointer items-center justify-center gap-2 rounded-full font-semibold whitespace-nowrap ' +
    'disabled:cursor-not-allowed disabled:opacity-40 ' +
    `${buttonSizes[size]} ${buttonVariants[variant]} ${extra}`
  )
}

export const inputClass =
  'h-11 w-full rounded-xl border border-line-strong bg-canvas px-3 text-sm text-ink placeholder:text-faint [color-scheme:dark]'

export const labelClass = 'text-[13px] font-semibold'

export const cardClass = 'rounded-xl border border-line bg-panel transition-[border-color] duration-200 hover:border-line-hover'

/** Pill toggle (filter chips, segmented options). */
export function chipClass(on: boolean, extra = '') {
  return (
    'inline-flex h-11 cursor-pointer items-center justify-center gap-2 rounded-full border px-4 text-[13px] font-semibold ' +
    (on ? 'border-ink bg-ink text-canvas ' : 'border-line-strong bg-panel text-ink hover:border-ink ') +
    extra
  )
}
