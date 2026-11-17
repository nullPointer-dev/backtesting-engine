import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { api, unwrap } from '../api/client'
import type { Backtest } from '../api/queries'
import { ButtonLink, Card, EmptyState, ErrorNote, IconButton, Loading, Mono, PageHeader } from '../components/ui'
import { monthRange, num, pct, plural, signed, signedRupee, toneClass } from '../lib/format'

const COLORS = ['#6aa7ff', '#b794f6', '#ffc857', '#4fd1c5', '#f687b3', '#a4a4ac', '#90cdf4', '#fbd38d']
const POINTS = 200

type Dir = 1 | -1 | 0
type MetricRow = { head: string } | { label: string; value(b: Backtest): number | null | undefined; format(v: number): string; dir: Dir }

const METRICS: MetricRow[] = [
  { head: 'Returns' },
  { label: 'Total return', value: (b) => b.total_return, format: (v) => pct(v), dir: 1 },
  { label: 'Net profit', value: (b) => b.net_profit, format: (v) => signedRupee(v), dir: 1 },
  { label: 'CAGR', value: (b) => b.cagr, format: (v) => pct(v), dir: 1 },
  { head: 'Risk-adjusted' },
  { label: 'Sharpe ratio', value: (b) => b.sharpe_ratio, format: (v) => signed(v), dir: 1 },
  { label: 'Sortino ratio', value: (b) => b.sortino_ratio, format: (v) => signed(v), dir: 1 },
  { label: 'Calmar ratio', value: (b) => b.calmar_ratio, format: (v) => signed(v), dir: 1 },
  { label: 'Recovery factor', value: (b) => b.recovery_factor, format: (v) => signed(v), dir: 1 },
  { head: 'Drawdown' },
  { label: 'Max drawdown', value: (b) => b.max_drawdown, format: (v) => pct(v), dir: 1 },
  { label: 'Max drawdown duration (bars)', value: (b) => b.max_drawdown_duration, format: (v) => num(v, 0), dir: -1 },
  { label: 'Ulcer index', value: (b) => b.ulcer_index, format: (v) => num(v), dir: -1 },
  { head: 'Trades' },
  { label: 'Total trades', value: (b) => b.total_trades, format: (v) => num(v, 0), dir: 0 },
  { label: 'Win rate', value: (b) => b.win_rate, format: (v) => `${num(v, 1)}%`, dir: 1 },
  { label: 'Profit factor', value: (b) => b.profit_factor, format: (v) => num(v), dir: 1 },
  { label: 'Expectancy per trade', value: (b) => b.expectancy, format: (v) => signedRupee(v), dir: 1 },
  { head: 'Costs and exposure' },
  { label: 'Exposure (share of bars in market)', value: (b) => b.exposure_pct, format: (v) => `${num(v, 1)}%`, dir: 0 },
  { label: 'Total commission', value: (b) => b.total_commission, format: (v) => num(v, 0), dir: -1 },
  { label: 'Skipped trades', value: (b) => b.skipped_trades, format: (v) => num(v, 0), dir: -1 },
]

/** Equity as % return since start, resampled to a fixed number of points. */
function returnPath(b: Backtest): number[] {
  const values = b.equity_curve.map((p) => p.equity).filter((v): v is number => v != null)
  if (values.length < 2) return []
  return Array.from({ length: POINTS }, (_, j) => {
    const v = values[Math.round((j / (POINTS - 1)) * (values.length - 1))]
    return (v / b.initial_capital - 1) * 100
  })
}

function ReturnChart({ runs }: { runs: { b: Backtest; color: string }[] }) {
  const paths = runs.map((r) => ({ ...r, values: returnPath(r.b) }))
  const all = paths.flatMap((p) => p.values)
  if (!all.length) return <p className="m-0 py-10 text-sm text-muted">No visible runs.</p>
  let lo = Math.min(0, ...all)
  let hi = Math.max(0, ...all)
  const pad = (hi - lo) * 0.06 || 1
  lo -= pad
  hi += pad
  const H = 320
  const y = (v: number) => ((hi - v) / (hi - lo)) * H
  const ticks = Array.from({ length: 5 }, (_, i) => hi - ((hi - lo) * i) / 4)
  return (
    <div className="flex gap-3">
      <div className="relative w-16 shrink-0 text-right font-mono text-[13px] text-subtle" style={{ height: H }} aria-hidden="true">
        {ticks.map((t, i) => (
          <span key={i} className="absolute right-0 -translate-y-1/2" style={{ top: `${(i / 4) * 100}%` }}>
            {pct(t, 0)}
          </span>
        ))}
      </div>
      <div className="relative min-w-0 flex-1 border-l border-line" style={{ height: H }}>
        <svg viewBox={`0 0 1000 ${H}`} preserveAspectRatio="none" className="absolute inset-0 h-full w-full" role="img" aria-label="Return since start for each run">
          {ticks.map((t, i) => (
            <line key={i} x1="0" x2="1000" y1={y(t)} y2={y(t)} stroke="#19191c" vectorEffect="non-scaling-stroke" />
          ))}
          <line x1="0" x2="1000" y1={y(0)} y2={y(0)} stroke="#45454d" strokeDasharray="4 4" vectorEffect="non-scaling-stroke" />
          {paths.map((p) => (
            <path
              key={p.b.backtest_id}
              d={p.values.map((v, i) => `${i ? 'L' : 'M'}${((i / (POINTS - 1)) * 1000).toFixed(1)} ${y(v).toFixed(1)}`).join('')}
              fill="none"
              stroke={p.color}
              strokeWidth="2"
              strokeLinejoin="round"
              vectorEffect="non-scaling-stroke"
            />
          ))}
        </svg>
      </div>
    </div>
  )
}

export function Compare() {
  const [params, setParams] = useSearchParams()
  const ids = (params.get('ids') ?? '')
    .split(',')
    .map(Number)
    .filter((n) => Number.isInteger(n) && n > 0)
    .slice(0, 20)
  const [hidden, setHidden] = useState<number[]>([])

  const compare = useQuery({
    queryKey: ['compare', ids],
    queryFn: () => unwrap(api.POST('/backtests/compare', { body: { backtest_ids: ids } })),
    enabled: ids.length > 0,
    retry: false,
  })

  const header = (
    <PageHeader
      breadcrumb={[{ label: 'Backtests', to: '/backtests' }, { label: 'Compare' }]}
      title="Compare backtests"
      subtitle={compare.data ? `${plural(compare.data.comparison.length, 'completed run')} side by side` : 'Completed runs side by side'}
      actions={
        <ButtonLink variant="secondary" to="/backtests?status=COMPLETED">
          Add or change runs
        </ButtonLink>
      }
    />
  )

  if (!ids.length || compare.error) {
    return (
      <>
        {header}
        {compare.error && <ErrorNote messages={[compare.error.message]} />}
        <EmptyState action={<ButtonLink to="/backtests?status=COMPLETED">Choose runs</ButtonLink>}>
          Tick two or more completed backtests on the Backtests page, then press Compare.
        </EmptyState>
      </>
    )
  }
  if (compare.isPending) return <Loading />

  const runs = compare.data.comparison.map((b, i) => ({ b, color: COLORS[i % COLORS.length] }))
  const remove = (id: number) => setParams({ ids: ids.filter((x) => x !== id).join(',') })

  // Best value per metric row, and how many rows each run wins.
  const table = METRICS.map((m) => {
    if ('head' in m) return m
    const values = runs.map(({ b }) => m.value(b) ?? null)
    const present = values.filter((v): v is number => v != null)
    // No winner when every run has the same value.
    const allEqual = present.length === runs.length && present.every((v) => v === present[0])
    const best = m.dir !== 0 && runs.length > 1 && present.length && !allEqual ? (m.dir > 0 ? Math.max(...present) : Math.min(...present)) : null
    return {
      ...m,
      hasBest: best != null,
      cells: values.map((v) => ({ text: v == null ? '—' : m.format(v), isBest: best != null && v === best })),
    }
  })
  const dataRows = table.filter((row): row is Exclude<typeof row, { head: string }> => !('head' in row))
  const rowsWithBest = dataRows.filter((row) => row.hasBest).length
  const wins = new Map(runs.map(({ b }, i) => [b.backtest_id, dataRows.filter((row) => row.cells[i].isBest).length]))

  return (
    <>
      {header}
      {ids.length > runs.length && (
        <p className="m-0 text-[13px] text-subtle">
          {plural(ids.length - runs.length, 'selected run')} left out because only completed backtests can be compared.
        </p>
      )}

      <section aria-label="Selected runs" className="grid grid-cols-[repeat(auto-fit,minmax(min(260px,100%),1fr))] gap-4">
        {runs.map(({ b, color }) => {
          const shown = !hidden.includes(b.backtest_id)
          return (
            <Card as="div" key={b.backtest_id} className="flex flex-col gap-4 p-5">
              <div className="flex items-start justify-between gap-3">
                <div className="flex min-w-0 items-start gap-2.5">
                  <span className="mt-1 size-3 shrink-0 rounded-full" style={{ background: color }} />
                  <div className="min-w-0">
                    <Link to={`/backtests/${b.backtest_id}`} className="text-sm font-semibold hover:underline">
                      {b.strategy_name} <span className="font-mono font-normal text-subtle">#{b.backtest_id}</span>
                    </Link>
                    <div className="mt-0.5 font-mono text-[13px] text-subtle">
                      {b.symbol} · {b.timeframe} · {monthRange(b.start_date, b.end_date)}
                    </div>
                  </div>
                </div>
                <IconButton label={`Remove ${b.strategy_name} from comparison`} size={36} onClick={() => remove(b.backtest_id)}>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
                    <path d="M6 6l12 12M18 6L6 18" />
                  </svg>
                </IconButton>
              </div>
              <div className="flex items-baseline justify-between gap-3">
                <Mono className={`text-[22px] font-semibold ${toneClass(b.total_return)}`}>{pct(b.total_return)}</Mono>
                {runs.length > 1 && (
                  <span className="text-xs text-muted">
                    best on {wins.get(b.backtest_id) ?? 0} of {rowsWithBest}
                  </span>
                )}
              </div>
              <button
                type="button"
                aria-pressed={shown}
                onClick={() => setHidden((h) => (shown ? [...h, b.backtest_id] : h.filter((x) => x !== b.backtest_id)))}
                className={`h-10 cursor-pointer rounded-full border border-line-strong text-[13px] font-semibold hover:border-ink ${shown ? 'bg-panel text-ink' : 'bg-transparent text-subtle'}`}
              >
                {shown ? 'Hide from chart' : 'Show on chart'}
              </button>
            </Card>
          )
        })}
      </section>

      <Card aria-label="Return comparison" className="flex flex-col gap-4 p-6">
        <div className="flex flex-wrap items-baseline justify-between gap-3">
          <h2 className="m-0 text-[15px] font-medium">Return since start</h2>
          <span className="text-[13px] text-subtle">Each equity curve as % of initial capital, stretched to the same width</span>
        </div>
        <ReturnChart runs={runs.filter((r) => !hidden.includes(r.b.backtest_id))} />
        <div className="ml-[76px] flex justify-between text-[13px] text-subtle">
          <span>Start</span>
          <span>End</span>
        </div>
      </Card>

      <Card aria-label="Metric comparison" className="flex flex-col">
        <div className="flex flex-wrap items-baseline justify-between gap-3 border-b border-line px-6 py-[18px]">
          <h2 className="m-0 text-[15px] font-medium">Metrics</h2>
          {runs.length > 1 && <span className="text-[13px] text-subtle">▲ marks the best value in each row</span>}
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[640px] border-collapse text-sm">
            <thead>
              <tr className="text-left">
                <th className="px-6 py-3.5 text-[11px] font-medium text-subtle">Metric</th>
                {runs.map(({ b, color }) => (
                  <th key={b.backtest_id} className="px-4 py-3.5 text-right text-xs font-semibold whitespace-nowrap">
                    <span className="mr-2 inline-block size-2.5 rounded-full" style={{ background: color }} />#{b.backtest_id}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {table.map((row) =>
                'head' in row ? (
                  <tr key={row.head}>
                    <td colSpan={runs.length + 1} className="border-t border-line bg-raised px-6 py-3 text-xs font-semibold text-subtle">
                      {row.head}
                    </td>
                  </tr>
                ) : (
                  <tr key={row.label}>
                    <td className="border-t border-panel-2 px-6 py-3 text-muted">{row.label}</td>
                    {row.cells.map((c, i) => (
                      <td key={i} className={`border-t border-panel-2 px-4 py-3 text-right font-mono ${c.isBest ? 'bg-gain/12 font-bold text-gain' : ''}`}>
                        {c.text}
                        <span className="inline-block w-3.5 text-right text-[11px]">{c.isBest ? '▲' : ''}</span>
                      </td>
                    ))}
                  </tr>
                ),
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </>
  )
}
