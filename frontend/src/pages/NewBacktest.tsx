import { useEffect, useMemo, useState, type ReactNode } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { ApiError, api, unwrap } from '../api/client'
import {
  useCreateBacktest,
  useReference,
  useRunBacktest,
  useStrategies,
  useSymbols,
  type BacktestCreate,
  type Strategy,
} from '../api/queries'
import { StrategyRules } from '../components/RuleView'
import { Button, ButtonLink, Card, EmptyState, ErrorNote, Loading, PageHeader } from '../components/ui'
import { day, rupee } from '../lib/format'
import { summarize, type StrategyJson } from '../lib/strategy'
import { chipClass, inputClass, labelClass } from '../lib/styles'

const TIMEFRAMES = ['1m', '5m', '15m', '30m', '60m', '1d', '1wk'] as const
type Timeframe = (typeof TIMEFRAMES)[number]
type Sizing = 'FIXED_QUANTITY' | 'PERCENT_OF_CAPITAL'

const PRESETS = [
  { label: 'No costs', commission: '0', slippage: '0' },
  { label: 'Low', commission: '0.03', slippage: '0.05' },
  { label: 'High', commission: '0.25', slippage: '0.1' },
]

interface Form {
  strategyId: number | null
  symbol: string
  timeframe: Timeframe
  start: string
  end: string
  capital: string
  sizing: Sizing
  quantity: string
  percent: string
  commission: string
  slippage: string
}

const isoDay = (value: string) => value.slice(0, 10)

function shiftYears(dayIso: string, years: number) {
  const d = new Date(dayIso + 'T00:00:00Z')
  d.setUTCFullYear(d.getUTCFullYear() + years)
  return d.toISOString().slice(0, 10)
}

function Fieldset({ legend, children }: { legend: string; children: ReactNode }) {
  return (
    <fieldset className="m-0 flex min-w-0 flex-col gap-5 rounded-xl border border-line bg-panel p-6">
      <legend className="-ml-2 px-2 text-base font-medium">{legend}</legend>
      {children}
    </fieldset>
  )
}

function Field({ id, label, hint, children }: { id: string; label: string; hint?: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-2">
      <label htmlFor={id} className={labelClass}>
        {label}
      </label>
      {children}
      {hint && <span className="text-[13px] text-subtle">{hint}</span>}
    </div>
  )
}

function strategyMeta(strategy: Strategy, categories: Map<string, string>) {
  const info = summarize(strategy.strategy_json as StrategyJson)
  const groups = [...new Set(info.indicators.map((i) => categories.get(i) ?? i))]
  const kind = groups.length ? groups.slice(0, 2).join(' + ') : 'Price rules'
  return `${kind} · ${info.hasShort ? 'long + short' : 'long only'}`
}

export function NewBacktest() {
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const strategies = useStrategies()
  const symbols = useSymbols()
  const reference = useReference()
  const create = useCreateBacktest()
  const run = useRunBacktest()

  const [form, setForm] = useState<Form | null>(null)
  const [serverErrors, setServerErrors] = useState<string[]>([])
  const set = <K extends keyof Form>(key: K, value: Form[K]) => setForm((f) => (f ? { ...f, [key]: value } : f))

  const coverage = useMemo(() => {
    const map = new Map<string, Map<string, { first: string; last: string; bars: number }>>()
    for (const s of symbols.data?.symbols ?? []) {
      map.set(s.symbol, new Map(s.timeframes.map((t) => [t.timeframe, { first: isoDay(t.first), last: isoDay(t.last), bars: t.bars }])))
    }
    return map
  }, [symbols.data])

  // Build the initial form once strategies and symbols are known; query
  // parameters (?strategy, ?symbol, ?from=<backtest id>) prefill it.
  useEffect(() => {
    if (form || !strategies.data || !symbols.data) return
    const list = strategies.data.strategies
    const fromId = params.get('from')
    const init = async () => {
      const source = fromId
        ? await unwrap(api.GET('/backtests/{backtest_id}', { params: { path: { backtest_id: Number(fromId) } } })).catch(() => null)
        : null
      const wantedStrategy = Number(params.get('strategy') ?? source?.strategy_id ?? NaN)
      const strategyId = list.find((s) => s.strategy_id === wantedStrategy)?.strategy_id ?? list[0]?.strategy_id ?? null
      const symbol = [params.get('symbol'), source?.symbol, 'RELIANCE.NS'].find((s) => s && coverage.has(s)) ?? [...coverage.keys()][0] ?? ''
      const available = coverage.get(symbol)
      const wantedTf = (params.get('timeframe') ?? source?.timeframe ?? '1d') as Timeframe
      const timeframe = available?.has(wantedTf) ? wantedTf : ((TIMEFRAMES.find((t) => available?.has(t)) ?? '1d') as Timeframe)
      const range = available?.get(timeframe)
      const end = source ? isoDay(source.end_date) : (range?.last ?? '')
      const start = source ? isoDay(source.start_date) : range ? [shiftYears(end, -3), range.first].sort().at(-1)! : ''
      setForm({
        strategyId,
        symbol,
        timeframe,
        start,
        end,
        capital: String(source?.initial_capital ?? 100000),
        sizing: (source?.position_sizing_type as Sizing) ?? 'PERCENT_OF_CAPITAL',
        quantity: String(source?.quantity ?? 10),
        percent: String(source?.position_size_percent ?? 100),
        commission: String(source?.commission_pct ?? 0.03),
        slippage: String(source?.slippage_pct ?? 0.05),
      })
    }
    init()
  }, [form, strategies.data, symbols.data, coverage, params])

  const categories = useMemo(
    () => new Map((reference.data?.indicators ?? []).map((i) => [i.name, i.category])),
    [reference.data],
  )

  const header = <PageHeader title="New backtest" breadcrumb={[{ label: 'Backtests', to: '/backtests' }, { label: 'New' }]} />
  if (strategies.error || symbols.error) {
    return (
      <>
        {header}
        <ErrorNote messages={[(strategies.error ?? symbols.error)!.message]} />
      </>
    )
  }
  if (strategies.data?.strategies.length === 0) {
    return (
      <>
        {header}
        <EmptyState action={<ButtonLink to="/strategies/new">New strategy</ButtonLink>}>
          You need a strategy before you can backtest it.
        </EmptyState>
      </>
    )
  }
  if (symbols.data?.symbols.length === 0) {
    return (
      <>
        {header}
        <EmptyState>
          There is no market data yet. Load it on the server with <code className="font-mono">python main.py</code>, then come back.
        </EmptyState>
      </>
    )
  }
  if (!strategies.data || !form) return <Loading />

  const strategy = strategies.data.strategies.find((s) => s.strategy_id === form.strategyId)
  const available = coverage.get(form.symbol)
  const range = available?.get(form.timeframe)

  // Request body and client-side checks (mirrors BacktestCreate on the server).
  const num = (v: string) => (v.trim() === '' ? NaN : Number(v))
  const capital = num(form.capital)
  const commission = num(form.commission)
  const slippage = num(form.slippage)
  const body: BacktestCreate = {
    strategy_id: form.strategyId ?? 0,
    symbol: form.symbol,
    timeframe: form.timeframe,
    start_date: `${form.start}T00:00:00+05:30`,
    end_date: `${form.end}T23:59:59+05:30`,
    initial_capital: capital,
    position_sizing_type: form.sizing,
    commission_pct: commission,
    slippage_pct: slippage,
    ...(form.sizing === 'FIXED_QUANTITY' ? { quantity: num(form.quantity) } : { position_size_percent: num(form.percent) }),
  }
  const errors: string[] = []
  if (!strategy) errors.push('strategy_id: pick a strategy')
  if (!range) errors.push(`no ${form.timeframe} data for ${form.symbol}`)
  if (!form.start || !form.end || form.end <= form.start) errors.push('end_date must be after start_date')
  if (range && (form.end < range.first || form.start > range.last)) errors.push(`dates are outside the data (${day(range.first)} → ${day(range.last)})`)
  if (!(capital > 0)) errors.push('initial_capital must be greater than 0')
  if (form.sizing === 'FIXED_QUANTITY' && !(num(form.quantity) > 0)) errors.push('quantity must be greater than 0')
  if (form.sizing === 'PERCENT_OF_CAPITAL' && !(num(form.percent) > 0 && num(form.percent) <= 100)) errors.push('position_size_percent must be between 0 and 100')
  if (!(commission >= 0 && commission <= 10)) errors.push('commission_pct must be between 0 and 10')
  if (!(slippage >= 0 && slippage <= 10)) errors.push('slippage_pct must be between 0 and 10')

  const roundTrip = { commission: 2 * (commission || 0) * 1000, slippage: 2 * (slippage || 0) * 1000 }
  const busy = create.isPending || run.isPending

  function pickSymbol(symbol: string) {
    const tfs = coverage.get(symbol)
    const timeframe = tfs?.has(form!.timeframe) ? form!.timeframe : ((TIMEFRAMES.find((t) => tfs?.has(t)) ?? form!.timeframe) as Timeframe)
    pickRange(symbol, timeframe)
  }

  function pickRange(symbol: string, timeframe: Timeframe) {
    const r = coverage.get(symbol)?.get(timeframe)
    setForm((f) => {
      if (!f) return f
      let { start, end } = f
      if (r) {
        // Keep the chosen dates where they still fit; otherwise use the last 3 years of data.
        if (!(start >= r.first && end <= r.last && start < end)) {
          end = r.last
          start = [shiftYears(r.last, -3), r.first].sort().at(-1)!
        }
      }
      return { ...f, symbol, timeframe, start, end }
    })
  }

  async function submit(andRun: boolean) {
    setServerErrors([])
    try {
      const created = await create.mutateAsync(body)
      if (andRun) {
        await run.mutateAsync(created.backtest_id)
        navigate(`/backtests/${created.backtest_id}/run`)
      } else {
        navigate('/backtests')
      }
    } catch (error) {
      setServerErrors(error instanceof ApiError ? error.messages : ['Could not create the backtest.'])
    }
  }

  return (
    <>
      <PageHeader
        breadcrumb={[{ label: 'Backtests', to: '/backtests' }, { label: 'New' }]}
        title={<span className="text-[34px]">New backtest</span>}
        subtitle="Pick a strategy, a market and a period. The request on the right updates as you go."
      />

      <div className="flex flex-wrap items-start gap-6">
        <form className="flex min-w-0 flex-[3_1_560px] flex-col gap-6" onSubmit={(e) => e.preventDefault()}>
          <Fieldset legend="Strategy">
            <div className="grid grid-cols-[repeat(auto-fit,minmax(min(200px,100%),1fr))] gap-3">
              {strategies.data.strategies.map((s) => {
                const on = s.strategy_id === form.strategyId
                return (
                  <button
                    key={s.strategy_id}
                    type="button"
                    aria-pressed={on}
                    onClick={() => set('strategyId', s.strategy_id)}
                    className={`flex min-h-[72px] cursor-pointer flex-col gap-1 rounded-xl border-2 px-4 py-3.5 text-left ${
                      on ? 'border-info bg-info/10' : 'border-line bg-panel hover:border-ink'
                    }`}
                  >
                    <span className="text-sm font-semibold">{s.name}</span>
                    <span className="text-xs text-muted">{strategyMeta(s, categories)}</span>
                  </button>
                )
              })}
            </div>
          </Fieldset>

          <Fieldset legend="Market">
            <div className="max-w-[320px]">
              <Field id="symbol" label="Symbol">
                <select id="symbol" value={form.symbol} onChange={(e) => pickSymbol(e.target.value)} className={`${inputClass} font-mono`}>
                  {[...coverage.keys()].map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
                </select>
              </Field>
            </div>
            <div role="group" aria-label="Timeframe" className="flex flex-col gap-2">
              <span className={labelClass}>Timeframe</span>
              <div className="flex flex-wrap gap-2">
                {TIMEFRAMES.map((tf) => {
                  const has = available?.has(tf)
                  return (
                    <button
                      key={tf}
                      type="button"
                      aria-pressed={form.timeframe === tf}
                      disabled={!has}
                      title={has ? undefined : `No ${tf} data for ${form.symbol}`}
                      onClick={() => pickRange(form.symbol, tf)}
                      className={chipClass(form.timeframe === tf, 'min-w-14 font-mono text-sm disabled:cursor-not-allowed disabled:opacity-35')}
                    >
                      {tf}
                    </button>
                  )
                })}
              </div>
              {range && (
                <span className="font-mono text-[13px] text-subtle">
                  Data from {day(range.first)} to {day(range.last)} · {range.bars.toLocaleString('en-IN')} bars
                </span>
              )}
            </div>
          </Fieldset>

          <Fieldset legend="Period and capital">
            <div className="grid grid-cols-[repeat(auto-fit,minmax(min(200px,100%),1fr))] gap-4">
              <Field id="start" label="Start date">
                <input id="start" type="date" value={form.start} min={range?.first} max={range?.last} onChange={(e) => set('start', e.target.value)} className={`${inputClass} font-mono`} />
              </Field>
              <Field id="end" label="End date">
                <input id="end" type="date" value={form.end} min={range?.first} max={range?.last} onChange={(e) => set('end', e.target.value)} className={`${inputClass} font-mono`} />
              </Field>
              <Field id="capital" label="Initial capital (₹)">
                <input id="capital" inputMode="decimal" value={form.capital} onChange={(e) => set('capital', e.target.value)} className={`${inputClass} font-mono`} />
              </Field>
            </div>
          </Fieldset>

          <Fieldset legend="Position sizing">
            <div role="group" aria-label="Sizing type" className="flex flex-wrap gap-2">
              {(
                [
                  ['FIXED_QUANTITY', 'Fixed quantity'],
                  ['PERCENT_OF_CAPITAL', 'Percent of capital'],
                ] as const
              ).map(([value, label]) => (
                <button key={value} type="button" aria-pressed={form.sizing === value} onClick={() => set('sizing', value)} className={chipClass(form.sizing === value, 'px-[18px] text-sm')}>
                  {label}
                </button>
              ))}
            </div>
            <div className="max-w-[240px]">
              {form.sizing === 'FIXED_QUANTITY' ? (
                <Field id="qty" label="Quantity (shares per trade)" hint="Capped at what the account can afford.">
                  <input id="qty" inputMode="decimal" value={form.quantity} onChange={(e) => set('quantity', e.target.value)} className={`${inputClass} font-mono`} />
                </Field>
              ) : (
                <Field id="pct" label="Position size (% of capital, 1–100)" hint="Of the equity at the time of each entry.">
                  <input id="pct" inputMode="decimal" value={form.percent} onChange={(e) => set('percent', e.target.value)} className={`${inputClass} font-mono`} />
                </Field>
              )}
            </div>
          </Fieldset>

          <Fieldset legend="Trading costs">
            <div role="group" aria-label="Cost presets" className="flex flex-wrap gap-2">
              {PRESETS.map((p) => {
                const on = Number(form.commission) === Number(p.commission) && Number(form.slippage) === Number(p.slippage)
                return (
                  <button
                    key={p.label}
                    type="button"
                    aria-pressed={on}
                    onClick={() => setForm((f) => (f ? { ...f, commission: p.commission, slippage: p.slippage } : f))}
                    className={chipClass(on, `h-10 px-3.5 font-medium ${on ? '' : 'bg-transparent'}`)}
                  >
                    {p.label}
                    <span className="font-mono text-xs opacity-70">
                      {p.commission}% / {p.slippage}%
                    </span>
                  </button>
                )
              })}
            </div>
            <div className="grid grid-cols-[repeat(auto-fit,minmax(min(240px,100%),1fr))] gap-4">
              <Field id="comm" label="Commission (% per side, 0–10)" hint="Charged on entry and again on exit, on the traded value.">
                <input id="comm" inputMode="decimal" value={form.commission} onChange={(e) => set('commission', e.target.value)} className={`${inputClass} font-mono`} />
              </Field>
              <Field id="slip" label="Slippage (% per fill, 0–10)" hint="Entries and exits both fill worse than the next bar's open by this much.">
                <input id="slip" inputMode="decimal" value={form.slippage} onChange={(e) => set('slippage', e.target.value)} className={`${inputClass} font-mono`} />
              </Field>
            </div>
            <div className="flex flex-wrap items-baseline justify-between gap-3 rounded-[10px] border border-line bg-canvas px-4 py-3.5">
              <span className="text-[13px] text-muted">One round trip per ₹1,00,000 traded</span>
              <span className="font-mono text-sm font-semibold">
                {rupee(roundTrip.commission + roundTrip.slippage)} ({((roundTrip.commission + roundTrip.slippage) / 1000).toFixed(2)}%){' '}
                <span className="font-normal text-subtle">
                  = {rupee(roundTrip.commission)} commission + {rupee(roundTrip.slippage)} slippage
                </span>
              </span>
            </div>
          </Fieldset>

          <ErrorNote title="The server rejected this backtest" messages={serverErrors} />

          <div className="flex flex-wrap items-center gap-3">
            <Button onClick={() => submit(true)} disabled={errors.length > 0 || busy}>
              {busy ? 'Starting…' : 'Create and run'}
            </Button>
            <Button variant="secondary" onClick={() => submit(false)} disabled={errors.length > 0 || busy}>
              Create only
            </Button>
            <Link to="/backtests" className="px-3 py-3 text-sm font-medium text-muted underline hover:text-ink">
              Cancel
            </Link>
          </div>
        </form>

        <aside className="flex min-w-0 flex-[2_1_340px] flex-col gap-6">
          {strategy && (
            <Card aria-label="Strategy rules" className="flex flex-col gap-4 p-6">
              <h2 className="m-0 text-base font-medium">{strategy.name}</h2>
              <StrategyRules json={strategy.strategy_json as StrategyJson} />
            </Card>
          )}
          <Card aria-label="Request preview" className="flex flex-col gap-4 p-6">
            <h2 className="m-0 text-base font-medium">Request</h2>
            <pre className="m-0 overflow-x-auto rounded-xl bg-canvas p-4 font-mono text-[12.5px] leading-relaxed text-ink-2">
              {JSON.stringify(body, (_, v) => (typeof v === 'number' && Number.isNaN(v) ? null : v), 2)}
            </pre>
            {errors.length ? (
              <ul className="m-0 flex flex-col gap-1 rounded-xl bg-loss/14 py-3 pr-3 pl-7 text-[13px] text-loss-soft">
                {errors.map((e) => (
                  <li key={e} className="font-mono">
                    {e}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="m-0 rounded-xl bg-gain/14 p-3 text-[13px] text-gain">Request is valid.</p>
            )}
          </Card>
        </aside>
      </div>
    </>
  )
}
