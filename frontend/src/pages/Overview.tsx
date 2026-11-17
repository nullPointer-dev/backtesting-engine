import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useBacktests, useDashboard, type BacktestStatus } from '../api/queries'
import { PlusIcon } from '../components/icons'
import { ButtonLink, Card, EmptyState, ErrorNote, Loading, Mono, PageHeader, StatusChip } from '../components/ui'
import { backtestHref, backtestNote } from '../lib/backtest'
import { monthRange, num, pct, toneClass } from '../lib/format'
import { chipClass } from '../lib/styles'

const FILTERS: { value: BacktestStatus | 'ALL'; label: string }[] = [
  { value: 'ALL', label: 'All' },
  { value: 'COMPLETED', label: 'Completed' },
  { value: 'RUNNING', label: 'Running' },
  { value: 'FAILED', label: 'Failed' },
  { value: 'CANCELLED', label: 'Cancelled' },
]

function Stat({ label, value, sub, tone = '' }: { label: string; value: string; sub: string; tone?: string }) {
  return (
    <Card as="div" className="flex flex-col gap-2 p-5">
      <span className="text-[13px] text-subtle">{label}</span>
      <Mono className={`text-[32px] font-semibold tracking-[-0.02em] ${tone}`}>{value}</Mono>
      <span className="text-[13px] text-subtle">{sub}</span>
    </Card>
  )
}

export function Overview() {
  const [filter, setFilter] = useState<BacktestStatus | 'ALL'>('ALL')
  const dashboard = useDashboard()
  const recent = useBacktests({ status: filter === 'ALL' ? undefined : filter, limit: 10 })
  const d = dashboard.data

  return (
    <>
      <PageHeader
        title={<span className="text-[34px]">Overview</span>}
        subtitle="Every backtest across your strategies, most recent first."
        actions={
          <ButtonLink to="/backtests/new">
            <PlusIcon /> New backtest
          </ButtonLink>
        }
      />

      {dashboard.error && <ErrorNote messages={[dashboard.error.message]} />}

      <section aria-label="Summary" className="grid grid-cols-[repeat(auto-fit,minmax(min(200px,100%),1fr))] gap-4">
        <Stat
          label="Total backtests"
          value={d ? num(d.total_backtests, 0) : '—'}
          sub={
            d
              ? `${d.completed_backtests} completed · ${d.running_backtests} running · ${d.failed_backtests} failed · ${d.cancelled_backtests} cancelled`
              : ' '
          }
        />
        <Stat label="Strategies" value={d ? num(d.total_strategies, 0) : '—'} sub="Saved rule sets" />
        <Stat label="Best return" value={pct(d?.best_return)} sub="Completed runs" tone={toneClass(d?.best_return)} />
        <Stat label="Average return" value={pct(d?.avg_return)} sub="Completed runs" />
        <Stat label="Worst return" value={pct(d?.worst_return)} sub="Completed runs" tone={toneClass(d?.worst_return)} />
      </section>

      <Card aria-label="Recent backtests" className="flex flex-col">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line px-6 py-5">
          <h2 className="m-0 text-base font-medium">Recent backtests</h2>
          <div role="group" aria-label="Filter by status" className="flex flex-wrap gap-2">
            {FILTERS.map((f) => (
              <button
                key={f.value}
                type="button"
                aria-pressed={filter === f.value}
                onClick={() => setFilter(f.value)}
                className={chipClass(filter === f.value)}
              >
                {f.label}
              </button>
            ))}
          </div>
        </div>

        {recent.isPending ? (
          <div className="px-6">
            <Loading />
          </div>
        ) : recent.error ? (
          <div className="p-6">
            <ErrorNote messages={[recent.error.message]} />
          </div>
        ) : recent.data.backtests.length === 0 ? (
          <div className="p-6">
            {filter === 'ALL' ? (
              <EmptyState action={<ButtonLink to="/backtests/new">New backtest</ButtonLink>}>
                No backtests yet. Pick a strategy and a market to run your first one.
              </EmptyState>
            ) : (
              <p className="m-0 text-sm text-muted">No {filter.toLowerCase()} backtests.</p>
            )}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[960px] border-collapse text-sm">
              <thead>
                <tr className="text-left text-[13px] text-subtle">
                  <th className="px-6 py-3.5 font-semibold">Strategy</th>
                  <th className="px-3 py-3.5 font-semibold">Symbol</th>
                  <th className="px-3 py-3.5 font-semibold">TF</th>
                  <th className="px-3 py-3.5 font-semibold">Period</th>
                  <th className="px-3 py-3.5 font-semibold">Status</th>
                  <th className="px-3 py-3.5 text-right font-semibold">Return</th>
                  <th className="px-3 py-3.5 text-right font-semibold">Sharpe</th>
                  <th className="px-3 py-3.5 text-right font-semibold">Max DD</th>
                  <th className="px-3 py-3.5 text-right font-semibold">Win rate</th>
                  <th className="py-3.5 pr-6 pl-3 text-right font-semibold">Trades</th>
                </tr>
              </thead>
              <tbody className="font-mono">
                {recent.data.backtests.map((b) => {
                  const done = b.status === 'COMPLETED'
                  return (
                    <tr key={b.backtest_id} className="[&>td]:border-t [&>td]:border-panel-2 hover:[&>td]:bg-row-hover">
                      <td className="px-6 py-3.5 font-sans">
                        <Link to={backtestHref(b)} className="font-semibold hover:underline">
                          {b.strategy_name ?? `Strategy ${b.strategy_id}`}
                        </Link>
                        <div className="mt-0.5 text-[13px] text-subtle">{backtestNote(b)}</div>
                      </td>
                      <td className="px-3 py-3.5 font-medium">{b.symbol}</td>
                      <td className="px-3 py-3.5 text-muted">{b.timeframe}</td>
                      <td className="px-3 py-3.5 whitespace-nowrap text-muted">{monthRange(b.start_date, b.end_date)}</td>
                      <td className="px-3 py-3.5 font-sans">
                        <StatusChip status={b.status} pulse />
                      </td>
                      <td className={`px-3 py-3.5 text-right font-semibold ${done ? toneClass(b.total_return) : 'text-subtle'}`}>
                        {done ? pct(b.total_return) : '—'}
                      </td>
                      <td className="px-3 py-3.5 text-right">{done ? num(b.sharpe_ratio) : '—'}</td>
                      <td className="px-3 py-3.5 text-right">{done ? pct(b.max_drawdown) : '—'}</td>
                      <td className="px-3 py-3.5 text-right">{done && b.win_rate != null ? `${num(b.win_rate, 1)}%` : '—'}</td>
                      <td className="py-3.5 pr-6 pl-3 text-right">{done ? num(b.total_trades, 0) : '—'}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </>
  )
}
