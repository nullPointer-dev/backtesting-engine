import { useCallback, useMemo, useState, type ReactNode } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ApiError, downloadFile } from '../api/client'
import {
  useBacktest,
  useDeleteBacktest,
  useHistory,
  useReturnsBreakdown,
  useRunBacktest,
  useStrategy,
  useTrades,
  type Backtest,
  type Trade,
} from '../api/queries'
import { TrashIcon } from '../components/icons'
import { StrategyRules } from '../components/RuleView'
import { SyncedCharts, type TradeSpan } from '../components/SyncedCharts'
import { Button, ButtonLink, Card, ErrorNote, IconButton, Loading, Mono, StatusChip } from '../components/ui'
import { sizingText } from '../lib/backtest'
import { day, dayRange, num, pct, plural, rupee, signedRupee, stamp, toneClass } from '../lib/format'
import { compactRupee, costBreakdown, pnlHistogram, tradeStats } from '../lib/results'
import type { StrategyJson } from '../lib/strategy'
import { chipClass } from '../lib/styles'

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

function Header({ b, actions }: { b: Backtest; actions?: ReactNode }) {
  return (
    <header className="flex flex-col gap-4">
      <nav aria-label="Breadcrumb" className="flex gap-2 text-[13px] text-subtle">
        <Link to="/backtests" className="underline hover:text-ink">
          Backtests
        </Link>
        <span aria-hidden="true">/</span>
        <span aria-current="page">#{b.backtest_id}</span>
      </nav>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="flex min-w-0 flex-col gap-2.5">
          <div className="flex flex-wrap items-center gap-3.5">
            <h1 className="m-0 text-[34px] font-semibold tracking-[-0.02em]">{b.strategy_name}</h1>
            <StatusChip status={b.status} pulse />
          </div>
          <p className="m-0 font-mono text-[15px] text-muted">
            {b.symbol} · {b.timeframe} · {dayRange(b.start_date, b.end_date)} · {sizingText(b)} · Initial capital {rupee(b.initial_capital)} ·
            Commission {b.commission_pct}% · Slippage {b.slippage_pct}%
          </p>
        </div>
        {actions && <div className="flex flex-wrap gap-2.5">{actions}</div>}
      </div>
    </header>
  )
}

/** Results for a backtest that has not completed: what happened and what to do next. */
function NotCompleted({ b }: { b: Backtest }) {
  const run = useRunBacktest()
  const navigate = useNavigate()
  const start = async () => {
    await run.mutateAsync(b.backtest_id)
    navigate(`/backtests/${b.backtest_id}/run`)
  }
  const copy = {
    PENDING: { title: 'Not run yet', body: 'This backtest was created but has not been run.', tone: 'border-line' },
    RUNNING: { title: 'Running now', body: 'Results appear here when the run completes.', tone: 'border-info' },
    FAILED: { title: 'Backtest failed', body: b.error_summary ?? 'The run stopped with an error.', tone: 'border-loss' },
    CANCELLED: { title: 'Backtest cancelled', body: 'The run was cancelled, so nothing was saved.', tone: 'border-warn' },
    COMPLETED: { title: '', body: '', tone: '' },
  }[b.status]
  return (
    <>
      <Header b={b} />
      <section className={`flex flex-col gap-4 rounded-xl border bg-panel p-6 ${copy.tone}`}>
        <h2 className="m-0 text-base font-medium">{copy.title}</h2>
        <p className={`m-0 text-sm ${b.status === 'FAILED' ? 'text-loss-soft' : 'text-muted'}`}>{copy.body}</p>
        {b.status === 'FAILED' && b.error_message && (
          <details className="text-[13px] text-subtle">
            <summary className="cursor-pointer">Technical details</summary>
            <pre className="mt-2 max-h-[320px] overflow-auto rounded-xl bg-canvas p-4 font-mono text-xs text-ink-2">{b.error_message}</pre>
          </details>
        )}
        <div className="flex flex-wrap gap-2.5">
          {b.status === 'RUNNING' ? (
            <ButtonLink to={`/backtests/${b.backtest_id}/run`}>Watch the run →</ButtonLink>
          ) : (
            <Button onClick={start} disabled={run.isPending}>
              {b.status === 'PENDING' ? 'Run now' : 'Run again'}
            </Button>
          )}
          <ButtonLink variant="secondary" to={`/strategies/${b.strategy_id}`}>
            Edit strategy
          </ButtonLink>
        </div>
        {run.error && <ErrorNote messages={(run.error as ApiError).messages ?? [run.error.message]} />}
      </section>
    </>
  )
}

type SortKey = 'n' | 'entry' | 'bars' | 'commission' | 'ret' | 'mae' | 'mfe' | 'pnl'
type Filter = 'ALL' | 'WIN' | 'LOSS' | 'LONG' | 'SHORT'

export function Results() {
  const id = Number(useParams().backtestId)
  const backtest = useBacktest(id)
  const b = backtest.data
  const completed = b?.status === 'COMPLETED'
  const trades = useTrades(id, completed)
  const history = useHistory(completed ? b.symbol : undefined, b?.timeframe, b?.start_date, b?.end_date)
  const returns = useReturnsBreakdown(id, completed)
  const strategy = useStrategy(b?.strategy_id)
  const remove = useDeleteBacktest()
  const navigate = useNavigate()

  const [hover, setHover] = useState<number | null>(null)
  const onHover = useCallback((i: number | null) => setHover(i), [])
  const [rangeDays, setRangeDays] = useState<number | null>(null)
  const [focusN, setFocusN] = useState<number | null>(null)
  const [sort, setSort] = useState<{ key: SortKey; dir: 1 | -1 }>({ key: 'n', dir: 1 })
  const [filter, setFilter] = useState<Filter>('ALL')
  const [year, setYear] = useState<string | null>(null)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [exportError, setExportError] = useState<string | null>(null)

  const bars = useMemo(() => history.data?.data ?? [], [history.data])
  const tradeList = useMemo(() => trades.data?.trades ?? [], [trades.data])

  // Line equity, drawdown and trades up with the price bars by timestamp.
  const series = useMemo(() => {
    const index = new Map(bars.map((bar, i) => [Date.parse(bar.datetime), i]))
    const equity = (b?.equity_curve ?? []).map((p) => p.equity ?? null)
    const aligned = equity.length === bars.length ? equity : bars.map(() => null)
    const drawdown: number[] = []
    let peak = b?.initial_capital ?? 0
    for (const v of aligned) {
      if (v != null) peak = Math.max(peak, v)
      drawdown.push(v != null && peak > 0 ? ((v - peak) / peak) * 100 : 0)
    }
    const spans: (TradeSpan & { n: number })[] = tradeList.map((t, i) => {
      const exit = index.get(Date.parse(t.exit_time)) ?? -1
      return {
        n: i + 1,
        entry: index.get(Date.parse(t.entry_time)) ?? -1,
        exit,
        held: t.exit_reason === 'END_OF_DATA' ? exit : exit - 1,
        side: t.side,
        win: t.pnl > 0,
      }
    })
    return { equity: aligned, drawdown, spans }
  }, [bars, b, tradeList])

  if (backtest.isPending) return <Loading />
  if (backtest.error || !b) return <ErrorNote messages={[backtest.error?.message ?? 'Backtest not found']} />
  if (!completed) return <NotCompleted b={b} />

  const focus = focusN != null ? series.spans[focusN - 1] ?? null : null
  const years = Math.max((Date.parse(b.end_date) - Date.parse(b.start_date)) / (365.25 * 86400_000), 0)
  const stats = tradeStats(tradeList)
  const costs = costBreakdown(tradeList, b.slippage_pct ?? 0)
  const hasShort = tradeList.some((t) => t.side === 'SHORT')

  // ---------------------------------------------------------------- hover readouts
  const hv = hover != null ? bars[hover] : null
  const hvPrev = hover != null && hover > 0 ? bars[hover - 1] : null
  const hvTrade = hover != null ? series.spans.find((s) => s.entry <= hover && hover <= s.held) : undefined
  const last = bars[bars.length - 1]
  const shownBar = hv ?? last
  const shownPrev = hv ? hvPrev : bars[bars.length - 2]
  const dayChange = shownBar && shownPrev ? ((shownBar.close - shownPrev.close) / shownPrev.close) * 100 : null

  // ---------------------------------------------------------------- KPI tiles
  const kpis = [
    { label: 'Total return', value: pct(b.total_return), sub: `${signedRupee(b.net_profit)} net`, tone: toneClass(b.total_return) },
    { label: 'CAGR', value: pct(b.cagr), sub: `over ${num(years, 1)} years`, tone: toneClass(b.cagr) },
    { label: 'Sharpe ratio', value: num(b.sharpe_ratio), sub: `Sortino ${num(b.sortino_ratio)}` },
    { label: 'Max drawdown', value: pct(b.max_drawdown), sub: `${plural(b.max_drawdown_duration ?? 0, 'bar')} underwater`, tone: 'text-loss' },
    { label: 'Win rate', value: b.win_rate != null ? `${num(b.win_rate, 1)}%` : '—', sub: `${stats.wins} of ${plural(b.total_trades ?? 0, 'trade')}` },
    { label: 'Profit factor', value: num(b.profit_factor), sub: `${signedRupee(b.expectancy)} per trade` },
    { label: 'Final capital', value: rupee(b.final_capital), sub: `from ${rupee(b.initial_capital)}` },
  ]

  const riskStats = [
    ['Sortino ratio', num(b.sortino_ratio)],
    ['Calmar ratio', num(b.calmar_ratio)],
    ['Recovery factor', num(b.recovery_factor)],
    ['Ulcer index', num(b.ulcer_index)],
    ['Max drawdown duration', plural(b.max_drawdown_duration ?? 0, 'bar')],
    ['Loss rate', b.loss_rate != null ? `${num(b.loss_rate, 1)}%` : '—'],
    ['Expectancy per trade', signedRupee(b.expectancy)],
    ['Average win / loss', `${signedRupee(stats.avgWin)} / ${signedRupee(stats.avgLoss)}`],
    ['Max consecutive wins', num(b.max_consecutive_wins, 0)],
    ['Max consecutive losses', num(b.max_consecutive_losses, 0)],
    ['Average trade duration', b.avg_trade_duration != null ? `${num(b.avg_trade_duration, 1)} bars` : '—'],
    ['Total trades', num(b.total_trades, 0)],
  ]

  // ---------------------------------------------------------------- monthly returns by year
  const monthly = returns.data?.monthly_returns ?? []
  const yearsList = [...new Set(monthly.map((m) => m.period.slice(0, 4)))]
  // Default to the latest year, unless it holds only a stub month or two (a range ending in early January).
  const monthsIn = (y: string) => monthly.filter((m) => m.period.startsWith(y)).length
  const latest = yearsList.at(-1)
  const defaultYear = latest && yearsList.length > 1 && monthsIn(latest) < 3 ? yearsList.at(-2) : latest
  const shownYear = year && yearsList.includes(year) ? year : defaultYear
  const yearMonths = new Map(monthly.filter((m) => m.period.startsWith(shownYear ?? '')).map((m) => [Number(m.period.slice(5, 7)) - 1, m]))
  const maxMonth = Math.max(0.01, ...[...yearMonths.values()].map((m) => Math.abs(m.return_pct)))
  const yearReturn = returns.data?.yearly_returns.find((y) => y.period === shownYear)?.return_pct

  // ---------------------------------------------------------------- P&L histogram and excursions
  const histogram = pnlHistogram(tradeList.map((t) => t.pnl))
  const maxCount = Math.max(1, ...histogram.buckets.map((h) => h.count))
  const maxExcursion = Math.max(0.01, ...tradeList.flatMap((t) => [Math.abs(t.mae_pct ?? 0), t.mfe_pct ?? 0]))
  const avgMae = tradeList.length ? tradeList.reduce((s, t) => s + (t.mae_pct ?? 0), 0) / tradeList.length : 0
  const avgMfe = tradeList.length ? tradeList.reduce((s, t) => s + (t.mfe_pct ?? 0), 0) / tradeList.length : 0

  // ---------------------------------------------------------------- trades table
  const rows = tradeList.map((t, i) => ({ t, n: i + 1 }))
  const filters: { value: Filter; label: string; count: number }[] = [
    { value: 'ALL', label: 'All', count: rows.length },
    { value: 'WIN', label: 'Winners', count: rows.filter((r) => r.t.pnl > 0).length },
    { value: 'LOSS', label: 'Losers', count: rows.filter((r) => r.t.pnl < 0).length },
    ...(hasShort
      ? [
          { value: 'LONG' as const, label: 'Long', count: rows.filter((r) => r.t.side === 'LONG').length },
          { value: 'SHORT' as const, label: 'Short', count: rows.filter((r) => r.t.side === 'SHORT').length },
        ]
      : []),
  ]
  const sortValue = (r: { t: Trade; n: number }): number =>
    ({
      n: r.n,
      entry: Date.parse(r.t.entry_time),
      bars: r.t.duration_bars,
      commission: r.t.commission ?? 0,
      ret: r.t.return_pct ?? 0,
      mae: r.t.mae_pct ?? 0,
      mfe: r.t.mfe_pct ?? 0,
      pnl: r.t.pnl,
    })[sort.key]
  const shown = rows
    .filter((r) => filter === 'ALL' || (filter === 'WIN' ? r.t.pnl > 0 : filter === 'LOSS' ? r.t.pnl < 0 : r.t.side === filter))
    .sort((a, z) => (sortValue(a) - sortValue(z)) * sort.dir)
  const columns: { label: string; key?: SortKey; align?: 'right' }[] = [
    { label: '#', key: 'n' },
    { label: 'Side' },
    { label: 'Entry', key: 'entry' },
    { label: 'Entry price', align: 'right' },
    { label: 'Exit' },
    { label: 'Exit price', align: 'right' },
    { label: 'Qty', align: 'right' },
    { label: 'Bars', key: 'bars', align: 'right' },
    { label: 'Exit reason' },
    { label: 'Commission', key: 'commission', align: 'right' },
    { label: 'Return', key: 'ret', align: 'right' },
    { label: 'MAE', key: 'mae', align: 'right' },
    { label: 'MFE', key: 'mfe', align: 'right' },
    { label: 'P&L', key: 'pnl', align: 'right' },
  ]
  const intraday = !['1d', '1wk'].includes(b.timeframe)
  const when = (iso: string) => (intraday ? stamp(iso) : day(iso))
  const qtyText = (q: number) => num(q, q % 1 ? 2 : 0)

  async function exportAs(format: 'json' | 'csv') {
    setExportError(null)
    try {
      await downloadFile(`/backtests/${id}/export?format=${format}`, `backtest_${id}.${format}`)
    } catch (error) {
      setExportError(error instanceof Error ? error.message : 'Export failed')
    }
  }

  const ranges: { label: string; days: number | null }[] = [
    { label: '3M', days: 92 },
    { label: '1Y', days: 366 },
    { label: '3Y', days: 1096 },
    { label: 'All', days: null },
  ].filter((r) => r.days == null || r.days < years * 365.25 * 0.9)

  return (
    <>
      <Header
        b={b}
        actions={
          confirmDelete ? (
            <div role="alertdialog" aria-label="Confirm delete" className="flex flex-wrap items-center gap-2.5 rounded-xl border border-loss bg-loss/10 px-3 py-2">
              <span className="text-[13px] text-loss-soft">Delete this backtest and its trades?</span>
              <Button
                variant="danger"
                size="xs"
                disabled={remove.isPending}
                onClick={async () => {
                  await remove.mutateAsync(id)
                  navigate('/backtests')
                }}
              >
                Delete
              </Button>
              <Button variant="secondary" size="xs" onClick={() => setConfirmDelete(false)}>
                Keep
              </Button>
            </div>
          ) : (
            <>
              <ButtonLink variant="secondary" to={`/backtests/new?from=${id}`}>
                New run
              </ButtonLink>
              <ButtonLink variant="secondary" to={`/compare?ids=${id}`}>
                Compare
              </ButtonLink>
              <Button variant="secondary" onClick={() => exportAs('csv')}>
                CSV
              </Button>
              <Button variant="secondary" onClick={() => exportAs('json')}>
                JSON
              </Button>
              <IconButton label="Delete backtest" tone="danger" size={40} className="size-11" onClick={() => setConfirmDelete(true)}>
                <TrashIcon />
              </IconButton>
            </>
          )
        }
      />
      {exportError && <ErrorNote messages={[exportError]} />}

      <section aria-label="Key metrics" className="grid grid-cols-[repeat(auto-fit,minmax(min(150px,100%),1fr))] gap-3 xl:grid-cols-7">
        {kpis.map((k) => (
          <Card as="div" key={k.label} className="flex min-w-0 flex-col gap-1.5 px-4 py-[18px]">
            <span className="text-[13px] text-subtle">{k.label}</span>
            <Mono className={`text-[22px] font-semibold tracking-[-0.02em] whitespace-nowrap ${k.tone ?? ''}`}>{k.value}</Mono>
            <span className="text-[13px] text-subtle">{k.sub}</span>
          </Card>
        ))}
      </section>

      {history.isPending ? (
        <Card className="p-6">
          <Loading label="Loading prices…" />
        </Card>
      ) : history.error ? (
        <ErrorNote messages={[history.error.message]} />
      ) : (
        <SyncedCharts
          bars={bars}
          equity={series.equity}
          drawdown={series.drawdown}
          spans={series.spans}
          capital={b.initial_capital}
          focus={focus}
          rangeDays={rangeDays}
          onHover={onHover}
          priceHeader={
            <>
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex flex-wrap items-baseline gap-3.5">
                  <h2 className="m-0 font-mono text-base font-medium">{b.symbol}</h2>
                  <span className="text-[13px] text-subtle">{b.timeframe} · NSE</span>
                  {shownBar && <Mono className="text-[13px] text-muted">{when(shownBar.datetime)}</Mono>}
                </div>
                <div role="group" aria-label="Chart range" className="inline-flex gap-0.5 rounded-full border border-line bg-canvas p-[3px]">
                  {ranges.map((r) => {
                    const on = !focus && rangeDays === r.days
                    return (
                      <button
                        key={r.label}
                        type="button"
                        aria-pressed={on}
                        onClick={() => {
                          setFocusN(null)
                          setRangeDays(r.days)
                        }}
                        className={`h-9 min-w-12 cursor-pointer rounded-full px-3.5 font-mono text-[13px] font-medium ${on ? 'bg-ink text-canvas' : 'text-muted hover:text-ink'}`}
                      >
                        {r.label}
                      </button>
                    )
                  })}
                </div>
              </div>
              <div className="flex flex-wrap items-center justify-between gap-3">
                {shownBar && (
                  <div className={`flex flex-wrap gap-4 font-mono text-[13px] ${toneClass(dayChange)}`}>
                    {(['open', 'high', 'low', 'close'] as const).map((k) => (
                      <span key={k}>
                        <span className="text-subtle">{k[0].toUpperCase()}</span> {num(shownBar[k])}
                      </span>
                    ))}
                    <span>{pct(dayChange)}</span>
                  </div>
                )}
                <div className="flex flex-wrap gap-4 text-[13px] text-muted">
                  <span className="inline-flex items-center gap-2">
                    <span className="text-gain">▲</span>Entry
                  </span>
                  <span className="inline-flex items-center gap-2">
                    <span className="text-loss">▼</span>Exit
                  </span>
                  <span className="text-subtle">Hover the chart to inspect a bar; scroll to zoom</span>
                </div>
              </div>
            </>
          }
          priceOverlay={
            hv && (
              <div className="pointer-events-none absolute top-3 left-3 z-10 flex min-w-[220px] animate-[line-in_.12s_ease-out] flex-col gap-1.5 rounded-xl border border-line bg-panel/95 px-3.5 py-3 shadow-lg">
                <Mono className="text-xs text-muted">{when(hv.datetime)}</Mono>
                <div className="grid grid-cols-2 gap-x-4 gap-y-1 font-mono text-[13px]">
                  {(['open', 'high', 'low', 'close'] as const).map((k) => (
                    <span key={k}>
                      <span className="text-subtle">{k[0].toUpperCase()}</span> {num(hv[k])}
                    </span>
                  ))}
                </div>
                <Mono className={`text-[13px] ${toneClass(dayChange)}`}>{pct(dayChange)} on the bar</Mono>
                <span className={`border-t border-line pt-2 text-xs ${hvTrade ? (hvTrade.win ? 'text-gain' : 'text-loss') : 'text-subtle'}`}>
                  {hvTrade ? `In trade #${hvTrade.n} · ${hvTrade.side.toLowerCase()} · ${hvTrade.win ? 'winner' : 'loser'}` : 'Flat: no open position'}
                </span>
              </div>
            )
          }
          equityHeader={
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex flex-wrap items-baseline gap-3.5">
                <h2 className="m-0 text-base font-medium">Equity curve</h2>
                <Mono className="text-[13px] text-subtle">{dayRange(b.start_date, b.end_date)}</Mono>
              </div>
              {hover != null && series.equity[hover] != null ? (
                <div className="flex flex-wrap gap-4 font-mono text-[13px]">
                  <span className="text-muted">{when(bars[hover].datetime)}</span>
                  <span>{rupee(series.equity[hover])}</span>
                  <span className={toneClass(series.equity[hover]! - b.initial_capital)}>{pct((series.equity[hover]! / b.initial_capital - 1) * 100)}</span>
                  <span className="text-loss">DD {pct(series.drawdown[hover])}</span>
                </div>
              ) : (
                <div className="flex flex-wrap gap-4 text-[13px] text-muted">
                  <span className="inline-flex items-center gap-2">
                    <span className="h-[3px] w-[18px] rounded-sm bg-info" />
                    Equity
                  </span>
                  <span className="inline-flex items-center gap-2">
                    <span className="size-3 rounded-[3px] border border-gain/50 bg-gain/18" />
                    Winning trade
                  </span>
                  <span className="inline-flex items-center gap-2">
                    <span className="size-3 rounded-[3px] border border-loss/50 bg-loss/18" />
                    Losing trade
                  </span>
                </div>
              )}
            </div>
          }
        />
      )}

      <div className="flex flex-wrap items-stretch gap-6">
        <Card aria-label="Monthly returns" className="flex min-w-0 flex-[1_1_460px] flex-col gap-4 p-6">
          <div className="flex flex-wrap items-baseline justify-between gap-3">
            <h2 className="m-0 text-base font-medium">Monthly returns</h2>
            <Mono className="text-[13px] text-subtle">
              {shownYear} · <span className={toneClass(yearReturn)}>{pct(yearReturn)}</span>
            </Mono>
          </div>
          {yearsList.length > 1 && (
            <div role="group" aria-label="Year" className="flex flex-wrap gap-1.5">
              {yearsList.map((y) => (
                <button key={y} type="button" aria-pressed={y === shownYear} onClick={() => setYear(y)} className={chipClass(y === shownYear, 'h-8 px-3 font-mono text-xs')}>
                  {y}
                </button>
              ))}
            </div>
          )}
          <div className="grid grid-cols-3 gap-2 sm:grid-cols-4 lg:grid-cols-6">
            {MONTHS.map((label, i) => {
              const m = yearMonths.get(i)
              const strength = m ? Math.min(1, Math.abs(m.return_pct) / maxMonth) : 0
              const bg = !m ? 'transparent' : m.return_pct >= 0 ? `rgba(46,189,133,${0.08 + strength * 0.42})` : `rgba(240,84,79,${0.08 + strength * 0.42})`
              return (
                <div key={label} className={`flex flex-col gap-1 rounded-xl p-3 ${m ? '' : 'border border-dashed border-line'}`} style={{ background: bg }}>
                  <span className="text-xs text-muted">{label}</span>
                  <Mono className="text-[15px] font-semibold">{m ? pct(m.return_pct) : '—'}</Mono>
                  <Mono className="text-xs text-muted">{m ? compactRupee(m.pnl) : ' '}</Mono>
                </div>
              )
            })}
          </div>
        </Card>

        <Card aria-label="Trade P&L distribution" className="flex min-w-0 flex-[1_1_400px] flex-col gap-4 p-6">
          <div className="flex flex-wrap items-baseline justify-between gap-3">
            <h2 className="m-0 text-base font-medium">Trade P&amp;L distribution</h2>
            <span className="text-[13px] text-subtle">
              {stats.wins} winners · {stats.losses} losers
            </span>
          </div>
          {histogram.buckets.length ? (
            <>
              <div className="flex h-[190px] items-end gap-2 border-b border-line-strong">
                {histogram.buckets.map((h) => (
                  <div key={h.from} className="flex h-full min-w-0 flex-1 flex-col items-center justify-end gap-1.5">
                    <Mono className="text-xs font-semibold">{h.count || ''}</Mono>
                    <div
                      className={`w-full rounded-t ${h.from >= 0 ? 'bg-gain' : 'bg-loss'}`}
                      style={{ height: `${(h.count / maxCount) * 150}px`, opacity: h.count ? 1 : 0 }}
                    />
                  </div>
                ))}
              </div>
              <div className="-mt-2 flex gap-2">
                {histogram.buckets.map((h) => (
                  <Mono key={h.from} className="min-w-0 flex-1 truncate text-center text-xs text-subtle">
                    {compactRupee(h.from)}
                  </Mono>
                ))}
              </div>
              <p className="m-0 text-[13px] text-subtle">Bucket width {rupee(histogram.width)}. Labels mark each bucket's lower edge.</p>
            </>
          ) : (
            <p className="m-0 text-sm text-muted">No trades.</p>
          )}
        </Card>
      </div>

      <div className="flex flex-wrap items-stretch gap-6">
        <Card aria-label="Trade excursions" className="flex min-w-0 flex-[3_1_520px] flex-col gap-4 p-6">
          <div className="flex flex-wrap items-baseline justify-between gap-3">
            <h2 className="m-0 text-base font-medium">MAE / MFE per trade</h2>
            <Mono className="text-[13px] text-subtle">
              Average MAE {pct(avgMae)} · Average MFE {pct(avgMfe)}
            </Mono>
          </div>
          <p className="m-0 text-[13px] leading-normal text-subtle">
            Maximum adverse excursion is the worst move against the trade while it was open; maximum favourable excursion is the best run-up. Both are
            percentages of the entry fill.
          </p>
          <div className="flex flex-wrap gap-[18px] text-xs text-muted">
            <span className="inline-flex items-center gap-2">
              <span className="h-2.5 w-3 bg-loss" />
              MAE (adverse)
            </span>
            <span className="inline-flex items-center gap-2">
              <span className="h-2.5 w-3 bg-gain" />
              MFE (favourable)
            </span>
          </div>
          <div className="flex max-h-[420px] flex-col gap-1.5 overflow-y-auto pr-1">
            {tradeList.map((t, i) => (
              <div key={t.trade_id} className="flex items-center gap-2.5 text-xs">
                <Mono className="w-7 shrink-0 text-right text-subtle">{i + 1}</Mono>
                <Mono className="w-14 shrink-0 text-right text-loss">{pct(t.mae_pct)}</Mono>
                <div className="flex h-3.5 min-w-0 flex-1 items-center">
                  <div className="flex flex-1 justify-end">
                    <div className="h-2.5 rounded-l-sm bg-loss" style={{ width: `${(Math.abs(t.mae_pct ?? 0) / maxExcursion) * 100}%` }} />
                  </div>
                  <div className="h-3.5 w-px bg-line-strong" />
                  <div className="flex-1">
                    <div className="h-2.5 rounded-r-sm bg-gain" style={{ width: `${((t.mfe_pct ?? 0) / maxExcursion) * 100}%` }} />
                  </div>
                </div>
                <Mono className="w-14 shrink-0 text-gain">{pct(t.mfe_pct)}</Mono>
                <Mono className={`w-20 shrink-0 text-right font-semibold ${toneClass(t.pnl)}`}>{compactRupee(t.pnl)}</Mono>
              </div>
            ))}
          </div>
        </Card>

        <Card aria-label="Costs and exposure" className="flex min-w-0 flex-[2_1_340px] flex-col gap-5 p-6">
          <h2 className="m-0 text-base font-medium">Costs and exposure</h2>
          <div className="flex flex-col">
            {[
              { label: 'Gross P&L before costs', value: signedRupee(costs.gross), tone: toneClass(costs.gross) },
              { label: 'Commission', value: signedRupee(-costs.commission), tone: 'text-loss' },
              { label: 'Slippage', value: signedRupee(-costs.slippage), tone: 'text-loss' },
              { label: 'Net P&L', value: signedRupee(costs.net), tone: toneClass(costs.net) },
            ].map((w, i) => (
              <div key={w.label} className={`flex items-baseline justify-between gap-3 py-3 ${i ? 'border-t border-panel-2' : ''} ${i === 3 ? 'border-line-strong' : ''}`}>
                <span className="text-sm text-muted">{w.label}</span>
                <Mono className={`text-[15px] font-semibold ${w.tone}`}>{w.value}</Mono>
              </div>
            ))}
          </div>
          <div className="flex flex-col gap-2">
            <div className="flex justify-between text-sm">
              <span className="text-muted">Exposure</span>
              <Mono className="font-semibold">{b.exposure_pct != null ? `${num(b.exposure_pct, 1)}%` : '—'}</Mono>
            </div>
            <div role="img" aria-label={`In the market ${num(b.exposure_pct ?? 0, 1)}% of bars`} className="h-2.5 overflow-hidden rounded-sm bg-panel-2">
              <div className="h-full bg-info" style={{ width: `${b.exposure_pct ?? 0}%` }} />
            </div>
            <span className="text-[13px] text-subtle">Share of bars with an open position.</span>
          </div>
          <dl className="m-0 flex flex-col">
            {[
              ['Total commission', rupee(b.total_commission)],
              ['Costs as share of gross P&L', costs.share != null ? `${num(costs.share, 1)}%` : '—'],
              ['Skipped trades', num(b.skipped_trades ?? 0, 0)],
            ].map(([k, v]) => (
              <div key={k} className="flex justify-between gap-3 border-t border-panel-2 py-3">
                <dt className="text-sm text-muted">{k}</dt>
                <dd className="m-0 font-mono text-[15px] font-semibold">{v}</dd>
              </div>
            ))}
          </dl>
          <p className="m-0 text-[13px] leading-normal text-subtle">
            A trade is skipped when the account cannot afford the entry. Fills happen at the next bar's open.
          </p>
        </Card>
      </div>

      <div className="flex flex-wrap items-stretch gap-6">
        <Card aria-label="Risk and trade statistics" className="flex min-w-0 flex-[3_1_520px] flex-col gap-4 p-6">
          <h2 className="m-0 text-base font-medium">Risk and trade statistics</h2>
          <dl className="m-0 grid grid-cols-[repeat(auto-fit,minmax(min(260px,100%),1fr))] gap-x-8">
            {riskStats.map(([label, value]) => (
              <div key={label} className="flex items-baseline justify-between gap-3 border-t border-panel-2 py-3">
                <dt className="text-sm text-muted">{label}</dt>
                <dd className="m-0 font-mono text-[15px] font-semibold">{value}</dd>
              </div>
            ))}
          </dl>
        </Card>
        <Card aria-label="Strategy rules" className="flex min-w-0 flex-[2_1_340px] flex-col gap-4 p-6">
          <div className="flex items-baseline justify-between gap-3">
            <h2 className="m-0 text-base font-medium">Strategy rules</h2>
            <Link to={`/strategies/${b.strategy_id}`} className="text-[13px] text-subtle hover:text-ink">
              Edit →
            </Link>
          </div>
          {strategy.data ? <StrategyRules json={strategy.data.strategy_json as StrategyJson} /> : <Loading />}
          <p className="m-0 text-xs text-faint">Shows the strategy as it is now; edits after this run aren't reflected in these results.</p>
        </Card>
      </div>

      <Card aria-label="Trades" className="flex flex-col">
        <div className="flex flex-wrap items-center justify-between gap-3 px-6 py-5">
          <div className="flex flex-col gap-1">
            <h2 className="m-0 text-base font-medium">Trades</h2>
            <span className="text-[13px] text-subtle">
              {shown.length === rows.length ? plural(rows.length, 'trade') : `${shown.length} of ${plural(rows.length, 'trade')}`} · commission and P&amp;L are
              net of costs
            </span>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {focus && (
              <button type="button" onClick={() => setFocusN(null)} className={chipClass(false, 'h-9 px-3')}>
                Charts zoomed to trade #{focusN} <span aria-hidden="true" className="text-subtle">✕</span>
              </button>
            )}
            <div role="group" aria-label="Filter trades" className="flex flex-wrap gap-1.5">
              {filters.map((f) => (
                <button key={f.value} type="button" aria-pressed={filter === f.value} onClick={() => setFilter(f.value)} className={chipClass(filter === f.value, 'h-9 px-3.5')}>
                  {f.label}
                  <span className="font-mono text-xs opacity-70">{f.count}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[1240px] border-collapse text-sm">
            <thead>
              <tr className="text-left text-[13px] text-subtle">
                {columns.map((c, i) => {
                  const active = sort.key === c.key
                  return (
                    <th
                      key={c.label}
                      aria-sort={active ? (sort.dir === 1 ? 'ascending' : 'descending') : undefined}
                      className={`h-12 font-medium whitespace-nowrap ${c.align === 'right' ? 'text-right' : ''} ${i === 0 ? 'pl-6' : 'px-3'} ${i === columns.length - 1 ? 'pr-6' : ''}`}
                    >
                      {c.key ? (
                        <button
                          type="button"
                          onClick={() => setSort({ key: c.key!, dir: active ? (sort.dir === 1 ? -1 : 1) : c.key === 'n' || c.key === 'entry' ? 1 : -1 })}
                          className={`inline-flex h-8 cursor-pointer items-center gap-1.5 rounded-lg px-1.5 hover:bg-panel-2 hover:text-ink ${active ? 'text-ink' : ''}`}
                        >
                          {c.label}
                          <span aria-hidden="true" className={`text-xs ${active ? 'text-info' : 'text-faint'}`}>
                            {active ? (sort.dir === 1 ? '↑' : '↓') : '↕'}
                          </span>
                        </button>
                      ) : (
                        c.label
                      )}
                    </th>
                  )
                })}
              </tr>
            </thead>
            <tbody className="font-mono">
              {shown.map(({ t, n }) => {
                const focused = focusN === n
                return (
                  <tr
                    key={t.trade_id}
                    className={`[&>td]:border-t [&>td]:border-panel-2 hover:[&>td]:bg-row-hover ${focused ? 'bg-info/10' : ''}`}
                    style={{ boxShadow: `inset 3px 0 0 ${focused ? 'var(--color-info)' : t.pnl > 0 ? 'rgba(46,189,133,0.6)' : 'rgba(240,84,79,0.6)'}` }}
                  >
                    <td className="py-2 pr-3 pl-6 font-sans">
                      <button
                        type="button"
                        aria-pressed={focused}
                        aria-label={focused ? `Stop focusing trade ${n}` : `Zoom charts to trade ${n}`}
                        onClick={() => setFocusN(focused ? null : n)}
                        className={`inline-flex h-8 cursor-pointer items-center gap-1.5 rounded-full border px-2.5 font-mono text-[13px] ${
                          focused ? 'border-info text-info' : 'border-line-strong text-muted hover:border-ink hover:text-ink'
                        }`}
                      >
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" aria-hidden="true">
                          <circle cx="11" cy="11" r="7" />
                          <path d="M20 20l-4-4" />
                        </svg>
                        {n}
                      </button>
                    </td>
                    <td className="px-3 py-3.5 font-sans">
                      <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${t.side === 'LONG' ? 'bg-info/14 text-info' : 'bg-violet/16 text-violet'}`}>{t.side}</span>
                    </td>
                    <td className="px-3 py-3.5 whitespace-nowrap">{when(t.entry_time)}</td>
                    <td className="px-3 py-3.5 text-right">{num(t.entry_price)}</td>
                    <td className="px-3 py-3.5 whitespace-nowrap">{when(t.exit_time)}</td>
                    <td className="px-3 py-3.5 text-right">{num(t.exit_price)}</td>
                    <td className="px-3 py-3.5 text-right">{qtyText(t.quantity)}</td>
                    <td className="px-3 py-3.5 text-right">{t.duration_bars}</td>
                    <td className="px-3 py-3.5">
                      <span className={`rounded-full px-2 py-0.5 text-[11px] ${t.exit_reason === 'END_OF_DATA' ? 'bg-warn/14 text-warn' : 'bg-panel-2 text-muted'}`}>{t.exit_reason}</span>
                    </td>
                    <td className="px-3 py-3.5 text-right">{rupee(t.commission, 2)}</td>
                    <td className={`px-3 py-3.5 text-right ${toneClass(t.return_pct)}`}>{pct(t.return_pct)}</td>
                    <td className="px-3 py-3.5 text-right text-loss">{pct(t.mae_pct)}</td>
                    <td className="px-3 py-3.5 text-right text-gain">{pct(t.mfe_pct)}</td>
                    <td className={`py-3.5 pr-6 pl-3 text-right font-semibold ${toneClass(t.pnl)}`}>{signedRupee(t.pnl, 2)}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
          {shown.length === 0 && <p className="m-0 px-6 py-8 text-sm text-muted">No trades match this filter.</p>}
        </div>
      </Card>
    </>
  )
}
