import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ApiError } from '../api/client'
import {
  useBacktest,
  useBacktestStatus,
  useCancelBacktest,
  useHistory,
  useRunBacktest,
  useTrades,
  type Backtest,
  type Trade,
} from '../api/queries'
import { LineChart, type Marker } from '../components/LineChart'
import { Button, ButtonLink, Card, ErrorNote, Loading, Mono } from '../components/ui'
import { sizingText } from '../lib/backtest'
import { day, dayRange, num, pct, plural, rupee } from '../lib/format'

const STEPS = ['Load market data', 'Preload indicators', 'Evaluate rules', 'Simulate portfolio', 'Compute metrics']
const STAGE_PHASE: Record<string, number> = { loading: 0, indicators: 1, signals: 2, portfolio: 3, metrics: 4, saving: 4, done: 5 }
const REPLAY_SECONDS = 8 // full replay at 1×

interface LogLine {
  t: string
  text: string
  tone?: 'info' | 'gain' | 'loss' | 'warn'
}

const toneClass = { info: 'text-info', gain: 'text-gain', loss: 'text-loss', warn: 'text-warn' }

function elapsed(startedAt: string | null | undefined) {
  if (!startedAt) return '+0.00s'
  return `+${Math.max(0, (Date.now() - new Date(startedAt).getTime()) / 1000).toFixed(2)}s`
}

/** Bars, equity and trades lined up by bar index for the replay. */
function useReplayData(backtest: Backtest | undefined, trades: Trade[] | undefined, closes: number[], times: string[]) {
  return useMemo(() => {
    const index = new Map(times.map((t, i) => [new Date(t).getTime(), i]))
    const equity = (backtest?.equity_curve ?? []).map((p) => p.equity ?? null)
    const placed = (trades ?? []).map((t) => ({
      trade: t,
      entry: index.get(new Date(t.entry_time).getTime()) ?? -1,
      exit: index.get(new Date(t.exit_time).getTime()) ?? -1,
    }))
    const markers: Marker[] = placed.flatMap(({ trade, entry, exit }) => [
      { index: entry, kind: 'entry' as const, side: trade.side },
      { index: exit, kind: 'exit' as const, side: trade.side },
    ])
    return { equity: equity.length === closes.length ? equity : [], placed, markers }
  }, [backtest, trades, closes, times])
}

export function Run() {
  const id = Number(useParams().backtestId)
  const status = useBacktestStatus(id)
  const backtest = useBacktest(id)
  const cancel = useCancelBacktest()
  const rerun = useRunBacktest()
  const s = status.data
  const b = backtest.data
  // Done once the full record (metrics, equity) has caught up with the status.
  const done = s?.status === 'COMPLETED' && b?.status === 'COMPLETED'

  // Refresh the full record (metrics, equity) when the run settles.
  const settled = s && !['PENDING', 'RUNNING'].includes(s.status) ? s.status : null
  const refetchBacktest = backtest.refetch
  useEffect(() => {
    if (settled) refetchBacktest()
  }, [settled, refetchBacktest])

  const history = useHistory(b?.symbol, b?.timeframe, b?.start_date, b?.end_date)
  const trades = useTrades(id, done)
  const closes = useMemo(() => (history.data?.data ?? []).map((bar) => bar.close), [history.data])
  const times = useMemo(() => (history.data?.data ?? []).map((bar) => bar.datetime), [history.data])
  const replay = useReplayData(done ? b : undefined, trades.data?.trades, closes, times)

  // ---------------------------------------------------------------- engine log
  const [log, setLog] = useState<LogLine[]>([])
  const lastMessage = useRef<string | null>(null)
  useEffect(() => {
    if (!s?.progress_message || s.progress_message === lastMessage.current) return
    lastMessage.current = s.progress_message
    const tone: LogLine['tone'] =
      s.status === 'COMPLETED' ? 'gain' : s.status === 'FAILED' ? 'loss' : s.status === 'CANCELLED' ? 'warn' : undefined
    const text =
      s.status === 'FAILED' ? `failed: ${s.error_summary ?? s.progress_message}` : s.status === 'COMPLETED' ? 'status=COMPLETED' : s.progress_message
    setLog((lines) => [...lines, { t: elapsed(s.started_at), text, tone }])
  }, [s])

  // ---------------------------------------------------------------- replay
  const n = closes.length
  const [pos, setPos] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [speed, setSpeed] = useState(1)
  const autoplayed = useRef(false)
  const ready = done && replay.equity.length > 0
  useEffect(() => {
    if (ready && !autoplayed.current) {
      autoplayed.current = true
      setPos(0)
      setPlaying(true)
    }
  }, [ready])
  useEffect(() => {
    if (!playing || !n) return
    let frame = 0
    let last = performance.now()
    const tick = (now: number) => {
      const step = ((now - last) / 1000) * (n / REPLAY_SECONDS) * speed
      last = now
      setPos((p) => {
        const next = Math.min(n - 1, p + step)
        if (next >= n - 1) setPlaying(false)
        return next
      })
      frame = requestAnimationFrame(tick)
    }
    frame = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frame)
  }, [playing, n, speed])

  if (status.isPending || backtest.isPending) return <Loading />
  if (status.error || backtest.error || !s || !b) {
    return <ErrorNote messages={[(status.error ?? backtest.error)?.message ?? 'Backtest not found']} />
  }

  const stage = s.progress_stage ?? ''
  const notStarted = s.status === 'PENDING' && (stage === '' || stage === 'cancelled')
  // Status says COMPLETED but the full record is still reloading: keep showing it as running.
  const finishing = s.status === 'COMPLETED' && !done
  const running = s.status === 'RUNNING' || (s.status === 'PENDING' && !notStarted) || finishing
  const cancelled = s.status === 'CANCELLED'
  const failed = s.status === 'FAILED'
  const phase = done ? 5 : STAGE_PHASE[stage] ?? -1
  const progress = done ? 100 : Math.round(s.progress_pct ?? 0)

  // Scan line while live: rule evaluation covers 10–80% of progress.
  const liveScan = running && stage === 'signals' && n ? Math.round(((progress - 10) / 70) * (n - 1)) : undefined
  const at = Math.floor(pos)
  const showReplay = ready

  // ---------------------------------------------------------------- live metrics at the replay position
  const capital = b.initial_capital
  const eqNow = showReplay ? (replay.equity[at] ?? capital) : capital
  const peak = showReplay ? Math.max(capital, ...replay.equity.slice(0, at + 1).map((v) => v ?? capital)) : capital
  const closed = replay.placed.filter((p) => p.exit >= 0 && p.exit <= at)
  const wins = closed.filter((p) => p.trade.pnl > 0).length
  const open = replay.placed.find((p) => p.entry <= at && at < p.exit)
  const inMarket = replay.placed.reduce((sum, p) => sum + Math.max(0, Math.min(at + 1, p.exit + (p.trade.exit_reason === 'END_OF_DATA' ? 1 : 0)) - p.entry), 0)
  const commission = closed.reduce((sum, p) => sum + (p.trade.commission ?? 0), 0)
  const live = [
    { label: 'Equity', value: rupee(eqNow) },
    { label: 'Return', value: pct((eqNow / capital - 1) * 100), tone: eqNow >= capital ? 'text-gain' : 'text-loss' },
    { label: 'Drawdown', value: pct(((eqNow - peak) / peak) * 100), tone: eqNow < peak * 0.99995 ? 'text-loss' : '' },
    { label: 'Trades closed', value: closed.length ? `${closed.length} · ${Math.round((wins / closed.length) * 100)}% won` : '0' },
    { label: 'Commission paid', value: rupee(commission), tone: commission > 0 ? 'text-loss' : '' },
    { label: 'Exposure', value: `${num(showReplay ? (inMarket / (at + 1)) * 100 : 0, 1)}%` },
    { label: 'Skipped trades', value: done ? num(b.skipped_trades ?? 0, 0) : '0' },
    {
      label: 'Position',
      value: open ? `${open.trade.side === 'LONG' ? 'Long' : 'Short'} ${num(open.trade.quantity, open.trade.quantity % 1 ? 2 : 0)}` : 'Flat',
      tone: open ? 'text-info' : 'text-muted',
    },
  ]

  const replayLog: LogLine[] = showReplay
    ? replay.placed.flatMap(({ trade, entry, exit }) => {
        const lines: (LogLine & { at: number })[] = []
        if (entry >= 0 && entry <= at)
          lines.push({ at: entry, t: `bar ${entry + 1}`, text: `${trade.side === 'LONG' ? 'buy' : 'sell short'} ${num(trade.quantity, 2)} @ ${num(trade.entry_price)}`, tone: 'info' })
        if (exit >= 0 && exit <= at)
          lines.push({ at: exit, t: `bar ${exit + 1}`, text: `${trade.side === 'LONG' ? 'sell' : 'cover'} @ ${num(trade.exit_price)} · ${trade.exit_reason} · P&L ${rupee(trade.pnl)}`, tone: trade.pnl >= 0 ? 'gain' : 'loss' })
        return lines
      }).sort((a, z) => a.at - z.at)
    : []
  const shownLog = [...log, ...replayLog].slice(-14)

  const chip = cancelled
    ? { text: 'CANCELLED', tone: 'bg-panel-2 text-subtle' }
    : failed
      ? { text: 'FAILED', tone: 'bg-loss/14 text-loss' }
      : done
        ? { text: 'COMPLETED', tone: 'bg-gain/14 text-gain' }
        : running && s.status !== 'PENDING'
          ? { text: 'RUNNING', tone: 'bg-info/14 text-info' }
          : { text: 'PENDING', tone: 'bg-panel-2 text-muted' }

  const barText = cancelled
    ? `Cancelled during ${['loading', 'indicator preload', 'rule evaluation', 'portfolio simulation', 'metrics'][Math.max(0, Math.min(phase, 4))]}`
    : failed
      ? s.error_summary ?? 'Failed'
      : done
        ? showReplay && pos < n - 1
          ? `${playing ? 'Replaying' : 'Paused'} · bar ${at + 1} / ${n}`
          : `All ${n.toLocaleString('en-IN')} bars processed`
        : finishing
          ? 'Loading results…'
          : notStarted
          ? 'Not started'
          : s.progress_message ?? 'Waiting for a worker…'

  async function runAgain() {
    lastMessage.current = null
    setLog([])
    autoplayed.current = false
    setPos(0)
    try {
      await rerun.mutateAsync(id)
    } catch {
      /* shown below */
    }
  }

  const summary = done
    ? [
        { label: 'Total return', value: pct(b.total_return), tone: (b.total_return ?? 0) >= 0 ? 'text-gain' : 'text-loss' },
        { label: 'Final capital', value: rupee(b.final_capital) },
        { label: 'Sharpe ratio', value: num(b.sharpe_ratio) },
        { label: 'Max drawdown', value: pct(b.max_drawdown), tone: 'text-loss' },
        { label: 'Win rate', value: b.win_rate != null ? `${num(b.win_rate, 1)}%` : '—' },
        { label: 'Profit factor', value: num(b.profit_factor) },
        { label: 'Exposure', value: b.exposure_pct != null ? `${num(b.exposure_pct, 1)}%` : '—' },
        { label: 'Total commission', value: rupee(b.total_commission), tone: 'text-loss' },
        { label: 'Skipped trades', value: num(b.skipped_trades ?? 0, 0) },
      ]
    : []
  const endOfData = (trades.data?.trades ?? []).filter((t) => t.exit_reason === 'END_OF_DATA').length
  const pending = cancel.isPending || rerun.isPending
  const actionError = (cancel.error ?? rerun.error) as ApiError | null

  return (
    <>
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div className="flex min-w-0 flex-col gap-2.5">
          <nav aria-label="Breadcrumb" className="flex gap-2 text-[13px] text-subtle">
            <Link to="/backtests" className="underline hover:text-ink">
              Backtests
            </Link>
            <span aria-hidden="true">/</span>
            <Link to={`/backtests/${id}`} className="hover:text-ink">
              #{id}
            </Link>
            <span aria-hidden="true">/</span>
            <span aria-current="page">run</span>
          </nav>
          <div className="flex flex-wrap items-center gap-3.5">
            <h1 className="m-0 text-[30px] font-semibold tracking-[-0.02em]">{b.strategy_name}</h1>
            <span role="status" className={`inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-xs font-semibold ${chip.tone}`}>
              <span className={`size-[7px] rounded-full bg-current ${running ? 'animate-pulse' : ''}`} />
              {chip.text}
            </span>
          </div>
          <p className="m-0 font-mono text-sm text-muted">
            {b.symbol} · {b.timeframe} · {dayRange(b.start_date, b.end_date)} · {sizingText(b)} · {rupee(b.initial_capital)} · Commission{' '}
            {b.commission_pct}% · Slippage {b.slippage_pct}%
          </p>
        </div>
        <div className="flex flex-wrap gap-2.5">
          {running && (
            <Button variant="secondary" className="border-warn text-warn hover:border-warn" disabled={pending} onClick={() => cancel.mutate(id)}>
              {cancel.isPending ? 'Cancelling…' : 'Cancel run'}
            </Button>
          )}
          {(cancelled || failed || notStarted) && (
            <>
              <ButtonLink variant="secondary" to="/backtests">
                All backtests
              </ButtonLink>
              <Button onClick={runAgain} disabled={pending}>
                {notStarted ? 'Run now' : 'Run again'}
              </Button>
            </>
          )}
          {done && (
            <ButtonLink variant="accent" to={`/backtests/${id}`}>
              View results →
            </ButtonLink>
          )}
        </div>
      </header>

      {actionError && <ErrorNote messages={actionError.messages ?? [actionError.message]} />}

      <Card aria-label="Progress" className="flex flex-col gap-4 px-6 py-5">
        <ol className="m-0 grid list-none grid-cols-[repeat(auto-fit,minmax(min(180px,100%),1fr))] gap-3 p-0">
          {STEPS.map((label, i) => {
            const state = i < phase ? 'done' : i === phase && running ? 'active' : i === phase && (cancelled || failed) ? 'stopped' : 'todo'
            const tone = { done: 'text-gain', active: 'text-info', stopped: cancelled ? 'text-warn' : 'text-loss', todo: 'text-faint' }[state]
            return (
              <li key={label} className={`flex items-center gap-2.5 text-[13px] ${tone}`}>
                <span
                  className={`inline-flex size-[18px] shrink-0 items-center justify-center rounded-full border-2 border-current text-[10px] font-bold text-canvas ${
                    state === 'done' ? 'bg-gain' : ''
                  } ${state === 'active' ? 'animate-pulse' : ''}`}
                >
                  {state === 'done' ? '✓' : state === 'stopped' ? <span className="text-current">×</span> : ''}
                </span>
                {label}
              </li>
            )
          })}
        </ol>
        <div className="flex flex-col gap-2">
          <div className="h-2.5 overflow-hidden rounded-sm bg-panel-2" role="progressbar" aria-valuenow={progress} aria-valuemin={0} aria-valuemax={100} aria-label="Backtest progress">
            <div
              className={`h-full transition-[width] duration-300 ${cancelled ? 'bg-subtle' : failed ? 'bg-loss' : done ? 'bg-gain' : 'bg-info'} ${
                running ? 'bg-[repeating-linear-gradient(45deg,transparent_0_8px,rgb(255_255_255/0.12)_8px_16px)]' : ''
              }`}
              style={{ width: `${showReplay ? ((at + 1) / n) * 100 : progress}%` }}
            />
          </div>
          <div className="flex flex-wrap justify-between gap-2 font-mono text-[13px] text-subtle">
            <span>{barText}</span>
            <span>{showReplay ? Math.round(((at + 1) / n) * 100) : progress}%</span>
          </div>
        </div>

        {showReplay && (
          <div className="flex flex-wrap items-center gap-3.5 border-t border-panel-2 pt-3.5">
            <button
              type="button"
              aria-label={playing ? 'Pause replay' : 'Play replay'}
              onClick={() => {
                if (!playing && pos >= n - 1) setPos(0)
                setPlaying(!playing)
              }}
              className="inline-flex size-11 shrink-0 cursor-pointer items-center justify-center rounded-full border border-line-strong bg-panel hover:border-ink"
            >
              {playing ? (
                <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                  <rect x="6" y="4" width="4" height="16" rx="1" />
                  <rect x="14" y="4" width="4" height="16" rx="1" />
                </svg>
              ) : (
                <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                  <path d="M7 4l13 8-13 8z" />
                </svg>
              )}
            </button>
            <label htmlFor="scrub" className="text-[13px] text-muted">
              Replay
            </label>
            <input
              id="scrub"
              type="range"
              min={0}
              max={n - 1}
              value={at}
              onChange={(e) => {
                setPlaying(false)
                setPos(Number(e.target.value))
              }}
              className="min-w-0 flex-[1_1_240px] cursor-pointer accent-info"
            />
            <div role="group" aria-label="Replay speed" className="inline-flex gap-0.5 rounded-full border border-line bg-canvas p-[3px]">
              {[1, 2, 4].map((v) => (
                <button
                  key={v}
                  type="button"
                  aria-pressed={speed === v}
                  onClick={() => setSpeed(v)}
                  className={`h-9 min-w-11 cursor-pointer rounded-full px-3 font-mono text-[13px] font-medium ${
                    speed === v ? 'bg-ink text-canvas' : 'text-muted hover:text-ink'
                  }`}
                >
                  {v}×
                </button>
              ))}
            </div>
          </div>
        )}
      </Card>

      <div className="flex flex-wrap items-start gap-6">
        <Card aria-label="Chart" className="flex min-w-0 flex-[3_1_560px] flex-col gap-4 p-6">
          <div className="flex flex-wrap items-baseline justify-between gap-3">
            <h2 className="m-0 font-mono text-[15px] font-medium">
              {b.symbol} <span className="font-normal text-subtle">{b.timeframe}</span>
            </h2>
            <Mono className="text-[13px] text-subtle">
              {n ? day(times[showReplay ? at : liveScan != null ? Math.max(0, liveScan) : n - 1]) : 'waiting for data'}
            </Mono>
          </div>
          {history.isPending ? (
            <Loading label="Loading prices…" />
          ) : (
            <LineChart
              label={`${b.symbol} closing price`}
              values={closes}
              height={300}
              color="#a4a4ac"
              markers={showReplay ? replay.markers : []}
              upTo={showReplay ? at + 1 : undefined}
              ghost={showReplay}
              scan={showReplay ? at : liveScan}
              format={(v) => num(v, v < 100 ? 2 : 0)}
            />
          )}
          <div className="flex flex-col gap-2.5 border-t border-panel-2 pt-4">
            <h3 className="m-0 text-sm font-semibold">
              Equity <span className="font-normal text-subtle">after commission and slippage</span>
            </h3>
            {showReplay ? (
              <LineChart
                label="Equity curve"
                values={replay.equity}
                height={150}
                color="#6aa7ff"
                area
                baseline={capital}
                upTo={at + 1}
                scan={at}
                ticks={3}
                format={(v) => rupee(v)}
              />
            ) : (
              <p className="m-0 flex h-[150px] items-center justify-center rounded-xl border border-dashed border-line text-[13px] text-subtle">
                {failed || cancelled ? 'No equity curve: nothing was saved.' : 'The equity curve appears when the run completes.'}
              </p>
            )}
          </div>
        </Card>

        <aside className="flex min-w-0 flex-[2_1_380px] flex-col gap-6">
          <section aria-label="Live metrics" className="grid grid-cols-2 gap-3">
            {live.map((k) => (
              <Card as="div" key={k.label} className="flex flex-col gap-1.5 px-4 py-3.5">
                <span className="text-[13px] text-subtle">{k.label}</span>
                <Mono className={`text-xl font-semibold ${k.tone ?? ''}`}>{k.value}</Mono>
              </Card>
            ))}
          </section>

          <section aria-label="Engine log" className="flex flex-col gap-2.5 rounded-xl border border-line bg-canvas p-4 font-mono">
            <div className="flex items-center justify-between text-[13px] text-subtle">
              <span>engine.log</span>
              <span>backtest_id={id}</span>
            </div>
            <div className="flex min-h-[250px] flex-col gap-1.5 text-xs leading-normal" aria-live="polite">
              {shownLog.length === 0 && <span className="text-subtle">{notStarted ? 'Not started yet.' : 'Waiting for the worker…'}</span>}
              {shownLog.map((line, i) => (
                <div key={i} className={`flex gap-2.5 ${line.tone ? toneClass[line.tone] : 'text-muted'}`}>
                  <span className="shrink-0 text-faint">{line.t}</span>
                  <span className="min-w-0 break-words">{line.text}</span>
                </div>
              ))}
              {running && <span className="animate-[blink_1s_steps(1)_infinite] text-subtle">▍</span>}
            </div>
          </section>
        </aside>
      </div>

      {cancelled && (
        <section role="status" aria-label="Run cancelled" className="flex flex-col gap-2.5 rounded-xl border border-warn bg-panel p-6">
          <div className="flex flex-wrap items-baseline justify-between gap-3">
            <h2 className="m-0 text-base font-medium text-warn">Backtest cancelled</h2>
            <span className="text-[13px] text-subtle">Stopped at {progress}% · no trades or equity curve were saved</span>
          </div>
          <p className="m-0 text-[13px] leading-relaxed text-muted">
            The run stops at its next checkpoint and is rolled back, so it has no results. You can run it again with the same settings.
          </p>
        </section>
      )}

      {failed && (
        <section role="alert" aria-label="Run failed" className="flex flex-col gap-3 rounded-xl border border-loss bg-panel p-6">
          <h2 className="m-0 text-base font-medium text-loss">Backtest failed</h2>
          <p className="m-0 text-sm text-loss-soft">{s.error_summary}</p>
          {s.error_message && s.error_message !== s.error_summary && (
            <details className="text-[13px] text-subtle">
              <summary className="cursor-pointer">Technical details</summary>
              <pre className="mt-2 max-h-[320px] overflow-auto rounded-xl bg-canvas p-4 font-mono text-xs text-ink-2">{s.error_message}</pre>
            </details>
          )}
        </section>
      )}

      {done && (
        <section aria-label="Run complete" className="flex flex-col gap-4 rounded-xl border border-gain bg-panel p-6">
          <div className="flex flex-wrap items-baseline justify-between gap-3">
            <h2 className="m-0 text-base font-medium text-gain">Backtest completed</h2>
            <span className="text-[13px] text-subtle">
              {plural(b.total_trades ?? 0, 'trade')} saved · equity curve saved
              {endOfData ? ` · ${plural(endOfData, 'trade')} closed by END_OF_DATA` : ''}
            </span>
          </div>
          <div className="grid grid-cols-[repeat(auto-fit,minmax(min(150px,100%),1fr))] gap-3">
            {summary.map((k) => (
              <div key={k.label} className="flex flex-col gap-1.5 rounded-xl border border-line bg-canvas px-4 py-3.5">
                <span className="text-[13px] text-subtle">{k.label}</span>
                <Mono className={`text-xl font-semibold ${k.tone ?? ''}`}>{k.value}</Mono>
              </div>
            ))}
          </div>
        </section>
      )}
    </>
  )
}
