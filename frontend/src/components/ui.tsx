import type { ButtonHTMLAttributes, ReactNode } from 'react'
import { Link, type LinkProps } from 'react-router-dom'
import type { Schemas } from '../api/client'
import { buttonClass, cardClass, type ButtonVariant } from '../lib/styles'

type Size = 'md' | 'sm' | 'xs'

export function Button({
  variant = 'primary',
  size = 'md',
  className = '',
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: ButtonVariant; size?: Size }) {
  return <button type="button" {...props} className={buttonClass(variant, size, className)} />
}

export function ButtonLink({
  variant = 'primary',
  size = 'md',
  className = '',
  ...props
}: LinkProps & { variant?: ButtonVariant; size?: Size }) {
  return <Link {...props} className={buttonClass(variant, size, className)} />
}

export function IconButton({
  label,
  tone = 'default',
  size = 40,
  className = '',
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { label: string; tone?: 'default' | 'danger'; size?: 36 | 40 }) {
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      {...props}
      style={{ width: size, height: size }}
      className={
        'inline-flex shrink-0 cursor-pointer items-center justify-center rounded-full border border-line-strong bg-panel ' +
        'hover:border-ink disabled:cursor-not-allowed disabled:opacity-35 ' +
        (tone === 'danger' ? 'text-loss ' : 'text-muted ') +
        className
      }
    />
  )
}

export function PageHeader({
  title,
  subtitle,
  actions,
  breadcrumb,
}: {
  title: ReactNode
  subtitle?: ReactNode
  actions?: ReactNode
  breadcrumb?: { label: string; to?: string }[]
}) {
  return (
    <header className="flex flex-wrap items-end justify-between gap-4">
      <div className="flex min-w-0 flex-col gap-2">
        {breadcrumb && (
          <nav aria-label="Breadcrumb" className="flex flex-wrap gap-2 text-[13px] text-subtle">
            {breadcrumb.map((crumb, i) => (
              <span key={i} className="flex gap-2">
                {i > 0 && <span aria-hidden="true">/</span>}
                {crumb.to ? (
                  <Link to={crumb.to} className="hover:text-ink">
                    {crumb.label}
                  </Link>
                ) : (
                  <span aria-current="page">{crumb.label}</span>
                )}
              </span>
            ))}
          </nav>
        )}
        <h1 className="m-0 text-[30px] font-semibold tracking-[-0.02em] break-words">{title}</h1>
        {subtitle && <p className="m-0 max-w-[640px] text-sm text-muted">{subtitle}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-3">{actions}</div>}
    </header>
  )
}

export function Card({
  children,
  className = '',
  as: Tag = 'section',
  ...rest
}: { children: ReactNode; className?: string; as?: 'section' | 'div' | 'article'; 'aria-label'?: string }) {
  return (
    <Tag {...rest} className={`${cardClass} ${className}`}>
      {children}
    </Tag>
  )
}

export function ErrorNote({ messages, title }: { messages: string[]; title?: string }) {
  if (!messages.length) return null
  return (
    <div role="alert" className="rounded-xl bg-loss/14 px-4 py-3 text-[13px] text-loss-soft">
      {title && <p className="m-0 mb-1 font-semibold">{title}</p>}
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

export function EmptyState({ children, action }: { children: ReactNode; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-start gap-4 rounded-xl border border-dashed border-line-strong bg-panel p-10 text-sm text-muted">
      <div>{children}</div>
      {action}
    </div>
  )
}

export function Loading({ label = 'Loading…' }: { label?: string }) {
  return (
    <div role="status" className="flex items-center gap-3 py-10 text-sm text-subtle">
      <span className="size-4 animate-spin rounded-full border-2 border-line-strong border-t-info" />
      {label}
    </div>
  )
}

type Status = Schemas['BacktestStatus']

const STATUS_TONE: Record<Status, string> = {
  COMPLETED: 'bg-gain/14 text-gain',
  RUNNING: 'bg-info/14 text-info',
  FAILED: 'bg-loss/14 text-loss',
  PENDING: 'bg-panel-2 text-muted',
  CANCELLED: 'bg-panel-2 text-subtle',
}

export function StatusChip({ status, pulse = false }: { status: Status; pulse?: boolean }) {
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold ${STATUS_TONE[status]}`}>
      <span className={`size-1.5 rounded-full bg-current ${pulse && status === 'RUNNING' ? 'animate-pulse' : ''}`} />
      {status}
    </span>
  )
}

export function Mono({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <span className={`font-mono ${className}`}>{children}</span>
}
