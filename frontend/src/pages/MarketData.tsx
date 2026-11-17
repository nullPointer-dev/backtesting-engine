import { useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useHistory, useSymbols } from '../api/queries'
import { CandleChart } from '../components/CandleChart'
import { ButtonLink, Card, EmptyState, ErrorNote, Loading, Mono, PageHeader } from '../components/ui'
import { day, num, pct, stamp, toneClass } from '../lib/format'
import { chipClass, inputClass } from '../lib/styles'

const TIMEFRAMES = ['1m', '5m', '15m', '30m', '60m', '1d', '1wk']
const LIMITS = [60, 120, 250, 1000]

export function MarketData() {
  const symbols = useSymbols()
  const [params, setParams] = useSearchParams()
  const [query, setQuery] = useState('')
  const [limit, setLimit] = useState(250)

  const list = useMemo(() => symbols.data?.symbols ?? [], [symbols.data])
  const symbol = list.find((s) => s.symbol === params.get('symbol')) ?? list.find((s) => s.symbol === 'RELIANCE.NS') ?? list[0]
  const available = new Map((symbol?.timeframes ?? []).map((t) => [t.timeframe as string, t]))
  const wantedTf = params.get('tf') ?? '1d'
  const tf = available.has(wantedTf) ? wantedTf : (TIMEFRAMES.find((t) => available.has(t)) ?? '1d')
  const intraday = !['1d', '1wk'].includes(tf)

  const history = useHistory(symbol?.symbol, tf)
  const bars = useMemo(() => (history.data?.data ?? []).slice(-limit), [history.data, limit])
  const last = bars.at(-1)
  const prev = bars.at(-2)
  const change = last && prev ? ((last.close - prev.close) / prev.close) * 100 : null

  const pick = (changes: Record<string, string>) =>
    setParams((current) => {
      const next = new URLSearchParams(current)
      for (const [k, v] of Object.entries(changes)) next.set(k, v)
      return next
    })

  const q = query.trim().toUpperCase()
  const groups = [
    { name: 'Indices', items: list.filter((s) => s.symbol.startsWith('^')) },
    { name: 'Stocks', items: list.filter((s) => !s.symbol.startsWith('^')) },
  ]
    .map((g) => ({ ...g, items: g.items.filter((s) => !q || s.symbol.includes(q)) }))
    .filter((g) => g.items.length)

  if (symbols.isPending) return <Loading />
  if (symbols.error) return <ErrorNote messages={[symbols.error.message]} />
  if (!list.length || !symbol) {
    return (
      <>
        <PageHeader title="Market data" />
        <EmptyState>
          No market data has been loaded yet. On the server, run <code className="font-mono">python main.py</code> for a full download, or{' '}
          <code className="font-mono">python main.py --update</code> to add recent bars.
        </EmptyState>
      </>
    )
  }

  const totalTfs = list.reduce((n, s) => n + s.timeframes.length, 0)

  return (
    <>
      <PageHeader title="Market data" subtitle={`${list.length} symbols · ${totalTfs} symbol–timeframe series loaded`} />

      <div className="flex flex-wrap items-start gap-6">
        <Card aria-label="Symbols" className="flex max-h-[calc(100vh-180px)] max-w-full flex-[0_0_260px] flex-col overflow-hidden max-lg:max-h-[360px] max-lg:flex-[1_1_100%]">
          <div className="flex flex-col gap-2 border-b border-line p-4">
            <label htmlFor="sq" className="text-[13px] text-subtle">
              Search symbols
            </label>
            <input id="sq" type="search" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="RELIANCE, ^NSEI…" className={`${inputClass} font-mono`} />
          </div>
          <div className="flex flex-col overflow-y-auto pt-2 pb-3">
            {groups.map((g) => (
              <div key={g.name}>
                <div className="px-4 pt-3 pb-1.5 text-[11px] font-semibold text-subtle">{g.name}</div>
                {g.items.map((s) => {
                  const on = s.symbol === symbol.symbol
                  return (
                    <button
                      key={s.symbol}
                      type="button"
                      aria-pressed={on}
                      onClick={() => pick({ symbol: s.symbol })}
                      className={`flex w-full cursor-pointer items-center justify-between px-4 py-2.5 text-left font-mono text-[13px] font-medium hover:bg-panel-2 ${
                        on ? 'bg-panel-2 text-ink shadow-[inset_2px_0_0_var(--color-gain)]' : 'text-muted'
                      }`}
                    >
                      <span>{s.symbol}</span>
                      <span className="text-[11px] font-normal text-subtle">{s.timeframes.length} tf</span>
                    </button>
                  )
                })}
              </div>
            ))}
            {!groups.length && <div className="p-4 text-[13px] text-subtle">No symbols match.</div>}
          </div>
        </Card>

        <div className="flex min-w-0 flex-[1_1_560px] flex-col gap-6">
          <Card aria-label="Price history" className="flex flex-col gap-5 p-6">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div className="flex flex-col gap-2">
                <div className="flex flex-wrap items-baseline gap-3">
                  <h2 className="m-0 font-mono text-2xl font-bold tracking-[-0.01em]">{symbol.symbol}</h2>
                  <Mono className="text-[13px] text-subtle">{tf}</Mono>
                </div>
                {last && (
                  <>
                    <div className="flex flex-wrap items-baseline gap-4 text-[13px]">
                      <Mono className="text-[22px] font-semibold">{num(last.close)}</Mono>
                      <Mono className={toneClass(change)}>{pct(change)}</Mono>
                      {(['open', 'high', 'low'] as const).map((k) => (
                        <span key={k}>
                          <span className="text-subtle">{k[0].toUpperCase()}</span> <Mono>{num(last[k])}</Mono>
                        </span>
                      ))}
                      <span>
                        <span className="text-subtle">Vol</span> <Mono>{num(last.volume, 0)}</Mono>
                      </span>
                    </div>
                    <Mono className="text-[13px] text-subtle">{intraday ? stamp(last.datetime) : day(last.datetime)}</Mono>
                  </>
                )}
              </div>
              <ButtonLink to={`/backtests/new?symbol=${encodeURIComponent(symbol.symbol)}&timeframe=${tf}`}>Backtest this symbol →</ButtonLink>
            </div>

            <div className="flex flex-wrap items-center justify-between gap-3">
              <div role="group" aria-label="Timeframe" className="flex flex-wrap gap-1.5">
                {TIMEFRAMES.map((t) => (
                  <button
                    key={t}
                    type="button"
                    aria-pressed={t === tf}
                    disabled={!available.has(t)}
                    title={available.has(t) ? undefined : `No ${t} data for ${symbol.symbol}`}
                    onClick={() => pick({ tf: t })}
                    className={chipClass(t === tf, 'min-w-13 px-3 font-mono disabled:cursor-not-allowed disabled:opacity-35')}
                  >
                    {t}
                  </button>
                ))}
              </div>
              <div role="group" aria-label="Bars to show" className="flex items-center gap-1.5">
                <span className="mr-1 text-[13px] text-subtle">bars</span>
                {LIMITS.map((n) => (
                  <button key={n} type="button" aria-pressed={n === limit} onClick={() => setLimit(n)} className={chipClass(n === limit, 'min-w-13 px-3 font-mono')}>
                    {n}
                  </button>
                ))}
              </div>
            </div>

            {history.isPending ? <Loading label="Loading bars…" /> : history.error ? <ErrorNote messages={[history.error.message]} /> : <CandleChart bars={bars} intraday={intraday} />}
          </Card>

          <div className="flex flex-wrap items-start gap-6">
            <Card aria-label="Coverage" className="flex min-w-0 flex-[1_1_380px] flex-col">
              <div className="border-b border-line px-5 py-[18px]">
                <h2 className="m-0 text-[15px] font-medium">Coverage</h2>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full min-w-[420px] border-collapse font-mono text-[13px]">
                  <thead>
                    <tr className="text-left font-sans text-[11px] text-subtle">
                      <th className="px-5 py-3 font-semibold">TF</th>
                      <th className="p-3 font-semibold">First</th>
                      <th className="p-3 font-semibold">Last</th>
                      <th className="py-3 pr-5 pl-3 text-right font-semibold">Bars</th>
                    </tr>
                  </thead>
                  <tbody>
                    {TIMEFRAMES.map((t) => {
                      const c = available.get(t)
                      const when = (iso: string) => (['1d', '1wk'].includes(t) ? day(iso) : stamp(iso))
                      return (
                        <tr key={t} className={`hover:[&>td]:bg-row-hover ${c ? '' : 'text-faint'}`}>
                          <td className="border-t border-panel-2 px-5 py-3 font-semibold">{t}</td>
                          <td className="border-t border-panel-2 p-3 text-muted">{c ? when(c.first) : '—'}</td>
                          <td className="border-t border-panel-2 p-3 text-muted">{c ? when(c.last) : '—'}</td>
                          <td className="border-t border-panel-2 py-3 pr-5 pl-3 text-right">{c ? c.bars.toLocaleString('en-IN') : '—'}</td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
              <p className="m-0 border-t border-line px-5 py-3.5 text-[13px] leading-normal text-subtle">
                1m to 60m keep a sliding window: the oldest rows are dropped as new bars arrive, so intraday backtests need recent dates.
              </p>
            </Card>

            <Card aria-label="Recent bars" className="flex min-w-0 flex-[1_1_460px] flex-col">
              <div className="border-b border-line px-5 py-[18px]">
                <h2 className="m-0 text-[15px] font-medium">Recent bars</h2>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full min-w-[520px] border-collapse font-mono text-[13px]">
                  <thead>
                    <tr className="text-left font-sans text-[11px] text-subtle">
                      <th className="px-5 py-3 font-semibold">{intraday ? 'Datetime' : 'Date'}</th>
                      {['Open', 'High', 'Low', 'Close'].map((h) => (
                        <th key={h} className="p-3 text-right font-semibold">
                          {h}
                        </th>
                      ))}
                      <th className="py-3 pr-5 pl-3 text-right font-semibold">Volume</th>
                    </tr>
                  </thead>
                  <tbody>
                    {bars
                      .slice(-8)
                      .reverse()
                      .map((b) => (
                        <tr key={b.datetime} className="hover:[&>td]:bg-row-hover">
                          <td className="border-t border-panel-2 px-5 py-3 whitespace-nowrap text-muted">{intraday ? stamp(b.datetime) : day(b.datetime)}</td>
                          <td className="border-t border-panel-2 p-3 text-right">{num(b.open)}</td>
                          <td className="border-t border-panel-2 p-3 text-right">{num(b.high)}</td>
                          <td className="border-t border-panel-2 p-3 text-right">{num(b.low)}</td>
                          <td className={`border-t border-panel-2 p-3 text-right ${b.close >= b.open ? 'text-gain' : 'text-loss'}`}>{num(b.close)}</td>
                          <td className="border-t border-panel-2 py-3 pr-5 pl-3 text-right text-muted">{num(b.volume, 0)}</td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
            </Card>
          </div>
        </div>
      </div>
    </>
  )
}
