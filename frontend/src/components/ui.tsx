import type { ButtonHTMLAttributes, ReactNode } from 'react'
import { Link, type LinkProps } from 'react-router-dom'

type Variant = 'primary' | 'secondary' | 'accent' | 'danger'

const variants: Record<Variant, string> = {
  primary: 'bg-ink text-canvas hover:bg-white',
  secondary: 'border border-line-strong bg-panel text-ink hover:border-ink',
  accent: 'bg-gain text-canvas hover:brightness-110',
  danger: 'border border-loss bg-loss text-canvas hover:brightness-110',
}

const buttonBase =
  'inline-flex h-11 items-center justify-center gap-2 rounded-md px-5 text-sm font-semibold ' +
  'cursor-pointer disabled:cursor-not-allowed disabled:opacity-50'

export function buttonClass(variant: Variant = 'primary', extra = '') {
  return `${buttonBase} ${variants[variant]} ${extra}`
}

export function Button({
  variant = 'primary',
  className = '',
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }) {
  return <button type="button" {...props} className={buttonClass(variant, className)} />
}

export function ButtonLink({ variant = 'primary', className = '', ...props }: LinkProps & { variant?: Variant }) {
  return <Link {...props} className={buttonClass(variant, className)} />
}

export function PageHeader({ title, subtitle, actions }: { title: ReactNode; subtitle?: ReactNode; actions?: ReactNode }) {
  return (
    <header className="flex flex-wrap items-end justify-between gap-4">
      <div className="flex flex-col gap-1.5">
        <h1 className="m-0 text-[30px] font-semibold tracking-[-0.02em]">{title}</h1>
        {subtitle && <p className="m-0 text-sm text-muted">{subtitle}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-3">{actions}</div>}
    </header>
  )
}

export function Panel({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <section className={`rounded-md border border-line bg-panel ${className}`}>{children}</section>
}

export function ErrorNote({ messages }: { messages: string[] }) {
  if (!messages.length) return null
  return (
    <div role="alert" className="rounded-md border border-loss bg-loss/10 px-4 py-3 text-[13px] text-loss-soft">
      {messages.length === 1 ? (
        messages[0]
      ) : (
        <ul className="m-0 flex list-disc flex-col gap-1 pl-4">
          {messages.map((m) => (
            <li key={m}>{m}</li>
          ))}
        </ul>
      )}
    </div>
  )
}
