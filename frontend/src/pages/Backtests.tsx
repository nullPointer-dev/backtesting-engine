import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { ApiError, downloadFile } from '../api/client'
import {
  useBacktests,
  useCancelBacktest,
  useDeleteBacktest,
  useRunBacktest,
  useStrategies,
  type BacktestStatus,
  type BacktestSummary,
} from '../api/queries'
import { PlusIcon } from '../components/icons'
import { ButtonLink, Card, EmptyState, ErrorNote, Loading, PageHeader, StatusChip } from '../components/ui'
import { backtestHref, sizingText } from '../lib/backtest'
import { day, monthRange, num, pct, signedRupee, toneClass } from '../lib/format'
import { buttonClass, chipClass } from '../lib/styles'

const PAGE_SIZE = 10
const STATUSES: (BacktestStatus | 'ALL')[] = ['ALL', 'PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED']
const label = (s: string) => s.charAt(0) + s.slice(1).toLowerCase()

type Action = { label: string; tone?: string; run(): void }

function Row({
  b,
  checked,
  onToggle,
  onError,
}: {
  b: BacktestSummary
  checked: boolean
  onToggle(): void
  onError(message: string): void
}) {
  const navigate = useNavigate()
  const run = useRunBacktest()
  const cancel = useCancelBacktest()
  const remove = useDeleteBacktest()
  const [confirming, setConfirming] = useState(false)
  const done = b.status === 'COMPLETED'
  const id = b.backtest_id
  const fail = (e: unknown) => onError(e instanceof ApiError ? e.messages[0] : 'Something went wrong')

  const actions: Action[] = []
  const start = { label: b.status === 'PENDING' ? 'Run' : 'Run again', tone: 'text-gain', run: () => run.mutateAsync(id).then(() => navigate(`/backtests/${id}/run`)).catch(fail) }
  const stop = { label: 'Cancel', tone: 'text-warn', run: () => cancel.mutateAsync(id).catch(fail) }
  const del = { label: 'Delete', tone: 'text-loss', run: () => setConfirming(true) }
  const exportAs = (format: 'json' | 'csv') => ({
    label: format.toUpperCase(),
    run: () => downloadFile(`/backtests/${id}/export?format=${format}`, `backtest_${id}.${format}`).catch(fail),
  })
  if (b.status === 'PENDING') actions.push(start, stop, del)
  else if (b.status === 'RUNNING') actions.push({ label: 'Watch', tone: 'text-info', run: () => navigate(`/backtests/${id}/run`) }, stop)
  else if (done) actions.push(exportAs('json'), exportAs('csv'), del)
  else actions.push(start, del)

  const sub = (b.status === 'FAILED' || b.status === 'CANCELLED') && b.error_summary ? b.error_summary : `${sizingText(b)} · created ${day(b.created_at)}`
  const busy = run.isPending || cancel.isPending || remove.isPending
  const cell = 'border-t border-panel-2 p-3 whitespace-nowrap'

  return (
    <tr className="hover:[&>td]:bg-row-hover">
      <td className={`${cell} pr-2 pl-5`}>
        <input
          type="checkbox"
          aria-label={`Select ${b.strategy_name} on ${b.symbol} for comparison`}
          title={done ? undefined : 'Only completed runs can be compared'}
          checked={checked}
          disabled={!done}
          onChange={onToggle}
          className="size-5 cursor-pointer accent-gain disabled:cursor-not-allowed disabled:opacity-30"
        />
      </td>
      <td className={cell}>
        <Link to={backtestHref(b)} className="font-semibold hover:underline">
          {b.strategy_name}
        </Link>
        <div className="mt-0.5 max-w-[280px] truncate text-[11px] text-subtle" title={sub}>
          {sub}
        </div>
      </td>
      <td className={`${cell} font-mono font-medium`}>{b.symbol}</td>
      <td className={`${cell} font-mono text-muted`}>{b.timeframe}</td>
      <td className={`${cell} font-mono whitespace-nowrap text-muted`}>{monthRange(b.start_date, b.end_date)}</td>
      <td className={cell}>
        <StatusChip status={b.status} pulse />
      </td>
      <td className={`${cell} text-right font-mono font-semibold ${done ? toneClass(b.total_return) : 'text-subtle'}`}>{done ? pct(b.total_return) : '—'}</td>
      <td className={`${cell} text-right font-mono ${done ? toneClass(b.net_profit) : 'text-subtle'}`}>{done ? signedRupee(b.net_profit) : '—'}</td>
      <td className={`${cell} text-right font-mono`}>{done ? pct(b.cagr) : '—'}</td>
      <td className={`${cell} text-right font-mono`}>{done ? num(b.sharpe_ratio) : '—'}</td>
      <td className={`${cell} text-right font-mono`}>{done ? pct(b.max_drawdown) : '—'}</td>
      <td className={`${cell} text-right font-mono`}>{done && b.win_rate != null ? `${num(b.win_rate, 1)}%` : '—'}</td>
      <td className={`${cell} text-right font-mono`}>{done ? num(b.profit_factor) : '—'}</td>
      <td className={`${cell} text-right font-mono`}>{done ? num(b.total_trades, 0) : '—'}</td>
      <td className={`${cell} pr-5`}>
        {confirming ? (
          <div role="alertdialog" aria-label="Confirm delete" className="flex items-center gap-1">
            <span className="text-xs text-loss-soft">Delete?</span>
            <button type="button" disabled={busy} onClick={() => remove.mutateAsync(id).catch(fail)} className="h-8 cursor-pointer rounded-full bg-loss px-2.5 text-xs font-semibold text-canvas">
              Yes
            </button>
            <button type="button" onClick={() => setConfirming(false)} className="h-8 cursor-pointer rounded-full px-2.5 text-xs font-semibold text-muted hover:bg-panel-2">
              No
            </button>
          </div>
        ) : (
          <div className="flex items-center gap-1">
            {actions.map((a) => (
              <button
                key={a.label}
                type="button"
                disabled={busy}
                onClick={a.run}
                className={`h-8 cursor-pointer rounded-full px-2 text-[13px] font-semibold hover:bg-panel-2 disabled:opacity-40 ${a.tone ?? 'text-muted'}`}
              >
                {a.label}
              </button>
            ))}
          </div>
        )}
      </td>
    </tr>
  )
}

export function Backtests() {
  const [params, setParams] = useSearchParams()
  const status = (params.get('status') as BacktestStatus | null) ?? 'ALL'
  const strategyId = params.get('strategy') ? Number(params.get('strategy')) : undefined
  const page = Math.max(0, Number(params.get('page') ?? 0))
  const [selected, setSelected] = useState<number[]>([])
  const [error, setError] = useState<string | null>(null)

  const strategies = useStrategies()
  const list = useBacktests({
    status: status === 'ALL' ? undefined : status,
    strategy_id: strategyId,
    skip: page * PAGE_SIZE,
    limit: PAGE_SIZE,
  })

  const update = (changes: Record<string, string | null>) =>
    setParams((current) => {
      const next = new URLSearchParams(current)
      for (const [k, v] of Object.entries(changes)) {
        if (v == null || v === '' || v === 'ALL' || (k === 'page' && v === '0')) next.delete(k)
        else next.set(k, v)
      }
      return next
    })

  const counts = list.data?.status_counts ?? {}
  const allCount = Object.values(counts).reduce((a, n) => a + n, 0)
  const total = list.data?.total ?? 0
  const from = total ? page * PAGE_SIZE + 1 : 0
  const to = Math.min(total, (page + 1) * PAGE_SIZE)
  const toggle = (id: number) => setSelected((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id].slice(-20)))

  return (
    <>
      <PageHeader
        title="Backtests"
        subtitle={list.data ? `${allCount.toLocaleString('en-IN')} backtests, newest first` : ' '}
        actions={
          <>
            {selected.length >= 2 ? (
              <ButtonLink variant="secondary" to={`/compare?ids=${selected.join(',')}`}>
                Compare {selected.length} runs
              </ButtonLink>
            ) : (
              <span className="text-[13px] text-subtle">
                {selected.length === 1 ? 'Tick one more completed run to compare' : 'Tick completed runs to compare them'}
              </span>
            )}
            <ButtonLink to="/backtests/new">
              <PlusIcon /> New backtest
            </ButtonLink>
          </>
        }
      />

      <div className="flex flex-wrap items-end justify-between gap-4">
        <div role="group" aria-label="Filter by status" className="flex flex-wrap gap-2">
          {STATUSES.map((s) => (
            <button key={s} type="button" aria-pressed={status === s} onClick={() => update({ status: s, page: null })} className={chipClass(status === s, 'px-3.5')}>
              {s === 'ALL' ? 'All' : label(s)}
              <span className="font-mono font-normal opacity-70">{s === 'ALL' ? allCount : counts[s] ?? 0}</span>
            </button>
          ))}
        </div>
        <div className="flex flex-col gap-1.5">
          <label htmlFor="strat" className="text-[13px] text-subtle">
            Strategy
          </label>
          <select
            id="strat"
            value={strategyId ?? ''}
            onChange={(e) => update({ strategy: e.target.value, page: null })}
            className="h-11 min-w-60 rounded-xl border border-line-strong bg-panel px-3 text-sm [color-scheme:dark]"
          >
            <option value="">All strategies</option>
            {strategies.data?.strategies.map((s) => (
              <option key={s.strategy_id} value={s.strategy_id}>
                {s.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {error && <ErrorNote messages={[error]} />}

      {list.isPending ? (
        <Loading />
      ) : list.error ? (
        <ErrorNote messages={[list.error.message]} />
      ) : allCount === 0 && status === 'ALL' && !strategyId ? (
        <EmptyState action={<ButtonLink to="/backtests/new">New backtest</ButtonLink>}>No backtests yet.</EmptyState>
      ) : (
        <Card aria-label="Backtests" className="flex flex-col">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[1340px] border-collapse text-sm">
              <thead>
                <tr className="text-left text-[11px] text-subtle">
                  <th className="w-7 py-3.5 pr-2 pl-5">
                    <span className="sr-only">Select for comparison</span>
                  </th>
                  {['Strategy', 'Symbol', 'TF', 'Period', 'Status'].map((h) => (
                    <th key={h} className="p-3.5 font-semibold">
                      {h}
                    </th>
                  ))}
                  {['Return', 'Net profit', 'CAGR', 'Sharpe', 'Max DD', 'Win', 'PF', 'Trades'].map((h) => (
                    <th key={h} className="p-3.5 text-right font-semibold">
                      {h}
                    </th>
                  ))}
                  <th className="py-3.5 pr-5 pl-3 font-semibold">Actions</th>
                </tr>
              </thead>
              <tbody>
                {list.data.backtests.map((b) => (
                  <Row key={b.backtest_id} b={b} checked={selected.includes(b.backtest_id)} onToggle={() => toggle(b.backtest_id)} onError={setError} />
                ))}
              </tbody>
            </table>
          </div>
          {list.data.backtests.length === 0 && <div className="border-t border-panel-2 p-10 text-sm text-muted">No backtests match these filters.</div>}
          <div className="flex flex-wrap items-center justify-between gap-3 border-t border-line px-5 py-4 text-[13px] text-subtle">
            <span>{total ? `Showing ${from}–${to} of ${total.toLocaleString('en-IN')}` : 'Nothing to show'}</span>
            <div className="flex gap-2">
              <button type="button" disabled={page === 0} onClick={() => update({ page: String(page - 1) })} className={buttonClass('secondary', 'md', 'px-4')}>
                Previous
              </button>
              <button type="button" disabled={to >= total} onClick={() => update({ page: String(page + 1) })} className={buttonClass('secondary', 'md', 'px-4')}>
                Next
              </button>
            </div>
          </div>
        </Card>
      )}
    </>
  )
}
