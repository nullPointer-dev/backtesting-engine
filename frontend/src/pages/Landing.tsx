import { Link } from 'react-router-dom'
import { useReference } from '../api/queries'
import { RuleTree } from '../components/RuleView'
import { Logo, LogoMark } from '../components/Logo'
import { canonicalJson, type StrategyJson } from '../lib/strategy'
import { buttonClass } from '../lib/styles'

// Counts that describe the product (kept in step with the backend's registry and assets list).
const STATS = [
  { n: '24', label: 'technical indicators' },
  { n: '8', label: 'comparison operators' },
  { n: '7', label: 'timeframes, 1 minute to 1 week' },
  { n: '112', label: 'NSE stocks and indices' },
]

const STEPS = [
  { n: '01', title: 'Compose the rules', body: 'Pick indicators, prices or fixed values and compare them. Group conditions with AND / OR for entries and exits, long and short.' },
  { n: '02', title: 'Choose a market', body: 'Select a symbol, a timeframe and a date range, then set capital, position sizing, commission and slippage.' },
  { n: '03', title: 'Read the results', body: 'Watch the run, replay it bar by bar, then dig into the equity curve, drawdown, monthly returns and every trade.' },
]

const ind = (indicator: string, period: number) => ({ type: 'indicator' as const, indicator, params: { period } })
const SAMPLE: StrategyJson = {
  long_entry: {
    type: 'group',
    operator: 'AND',
    children: [
      { type: 'condition', left: ind('SMA', 20), operator: 'crosses_above', right: ind('SMA', 50) },
      {
        type: 'group',
        operator: 'OR',
        children: [
          { type: 'condition', left: ind('RSI', 14), operator: '>', right: { type: 'value', value: 45 } },
          { type: 'condition', left: { type: 'price', field: 'close' }, operator: '>', right: ind('EMA', 100) },
        ],
      },
    ],
  },
  long_exit: { type: 'condition', left: ind('SMA', 20), operator: 'crosses_below', right: ind('SMA', 50) },
}

const FALLBACK_CATALOG: [string, string[]][] = [
  ['Moving Averages', ['SMA', 'EMA', 'WMA', 'VWMA']],
  ['Momentum', ['RSI', 'ROC', 'MOM', 'CCI']],
  ['MACD', ['MACD_LINE', 'MACD_SIGNAL', 'MACD_HISTOGRAM']],
  ['Stochastics', ['STOCH_K', 'STOCH_D', 'STOCHRSI_K', 'STOCHRSI_D']],
  ['Volatility', ['ATR', 'BB_UPPER', 'BB_MIDDLE', 'BB_LOWER']],
  ['Trend', ['ADX', 'SUPERTREND']],
  ['Volume', ['OBV', 'MFI', 'CMF']],
]
const OPERATORS = ['>', '<', '>=', '<=', '==', '!=', 'crosses_above', 'crosses_below']

/** Deterministic illustrative candles for the hero (not market data). */
function heroCandles() {
  let seed = 4242
  const rnd = () => {
    seed = (seed + 0x6d2b79f5) | 0
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
  const out: { o: number; c: number; h: number; l: number }[] = []
  let px = 100
  for (let i = 0; i < 70; i++) {
    const o = px
    px += (rnd() - 0.44) * 6 + 0.35
    out.push({ o, c: px, h: Math.max(o, px) + rnd() * 3 + 0.5, l: Math.min(o, px) - rnd() * 3 - 0.5 })
  }
  return out
}
const CANDLES = heroCandles()
const MARKS: [number, 'entry' | 'exit'][] = [
  [8, 'entry'],
  [24, 'exit'],
  [34, 'entry'],
  [51, 'exit'],
  [58, 'entry'],
]

function HeroChart() {
  const H = 320
  const lo = Math.min(...CANDLES.map((c) => c.l)) - 2
  const hi = Math.max(...CANDLES.map((c) => c.h)) + 2
  const y = (v: number) => ((hi - v) / (hi - lo)) * H
  const w = 1000 / CANDLES.length
  return (
    <div className="relative mx-[18px] my-[18px] h-[320px]">
      <svg viewBox={`0 0 1000 ${H}`} preserveAspectRatio="none" className="absolute inset-0 h-full w-full [clip-path:inset(0_100%_0_0)] motion-safe:animate-[reveal_7s_ease-out_forwards] motion-reduce:[clip-path:none]" aria-hidden="true">
        {CANDLES.map((c, i) => {
          const x = (i + 0.5) * w
          const up = c.c >= c.o
          const color = up ? '#2ebd85' : '#f0544f'
          return (
            <g key={i}>
              <line x1={x} x2={x} y1={y(c.h)} y2={y(c.l)} stroke={color} strokeWidth="1.5" vectorEffect="non-scaling-stroke" />
              <rect x={x - w * 0.3} width={w * 0.6} y={Math.min(y(c.o), y(c.c))} height={Math.max(1, Math.abs(y(c.o) - y(c.c)))} fill={color} />
            </g>
          )
        })}
      </svg>
      {MARKS.map(([i, kind]) => (
        <span
          key={i}
          aria-hidden="true"
          className={`absolute -translate-x-1/2 text-xs opacity-0 motion-safe:animate-[line-in_.4s_ease-out_forwards] motion-reduce:opacity-100 ${kind === 'entry' ? 'text-info' : 'text-ink'}`}
          style={{
            left: `${((i + 0.5) / CANDLES.length) * 100}%`,
            top: `${((kind === 'entry' ? y(CANDLES[i].l) + 6 : y(CANDLES[i].h) - 18) / H) * 100}%`,
            animationDelay: `${((i + 0.5) / CANDLES.length) * 4.9}s`,
          }}
        >
          {kind === 'entry' ? '▲' : '▼'}
        </span>
      ))}
    </div>
  )
}

const navLink = 'inline-flex h-11 items-center px-3 text-sm font-medium text-muted hover:text-ink'

export function Landing() {
  const reference = useReference()
  const catalog: [string, string[]][] = reference.data
    ? Object.entries(
        reference.data.indicators.reduce<Record<string, string[]>>((groups, i) => {
          ;(groups[i.category] ??= []).push(i.name)
          return groups
        }, {}),
      )
    : FALLBACK_CATALOG

  return (
    <div className="min-h-screen bg-canvas">
      <header className="border-b border-line">
        <div className="mx-auto flex min-h-[72px] max-w-[1240px] flex-wrap items-center justify-between gap-4 px-8 max-md:px-4">
          <Link to="/">
            <Logo />
          </Link>
          <nav aria-label="Primary" className="flex flex-wrap items-center gap-1">
            <a href="#how" className={`${navLink} max-md:hidden`}>
              How it works
            </a>
            <a href="#builder" className={`${navLink} max-md:hidden`}>
              Builder
            </a>
            <a href="#catalog" className={`${navLink} max-md:hidden`}>
              Indicators
            </a>
            <Link to="/login" className={navLink}>
              Sign in
            </Link>
            <Link to="/login?mode=register" className={buttonClass('primary', 'md', 'ml-2')}>
              Get started
            </Link>
          </nav>
        </div>
      </header>

      <main>
        <section aria-label="Hero" className="mx-auto flex max-w-[1240px] flex-wrap items-center gap-12 px-8 pt-[88px] pb-[72px] max-md:px-4 max-md:pt-12">
          <div className="flex min-w-0 flex-[1_1_440px] flex-col gap-6">
            <span className="self-start rounded-full border border-line-strong px-3 py-1.5 font-mono text-xs text-muted">NSE candles · 1m to 1wk</span>
            <h1 className="m-0 text-[52px] leading-[1.05] font-bold tracking-[-0.035em] max-md:text-[38px]">
              Describe a strategy.
              <br />
              <span className="text-gain">Watch it trade.</span>
            </h1>
            <p className="m-0 max-w-[520px] text-base leading-relaxed text-muted">
              Build entry and exit rules from AND / OR blocks, run them against historical candles, and read Sharpe, drawdown and every trade on one
              screen. Each strategy is plain JSON you can version and share.
            </p>
            <div className="flex flex-wrap gap-3">
              <Link to="/login?mode=register" className={buttonClass('primary', 'md', 'h-[52px] px-6 text-[15px]')}>
                Start backtesting →
              </Link>
              <a href="#how" className={buttonClass('secondary', 'md', 'h-[52px] px-6 text-[15px]')}>
                See how it works
              </a>
            </div>
          </div>

          <figure className="m-0 flex min-w-0 flex-[1_1_520px] flex-col overflow-hidden rounded-xl border border-line bg-panel">
            <figcaption className="flex flex-wrap items-center justify-between gap-3 border-b border-line px-[18px] py-3.5 text-[13px] text-muted">
              <span className="inline-flex items-center gap-2.5">
                <LogoMark size={18} />
                Rules replayed on every bar
              </span>
              <span className="font-mono text-xs text-subtle">Illustration</span>
            </figcaption>
            <HeroChart />
            <div className="grid grid-cols-3 border-t border-line">
              {[
                ['Entries', '▲ next open', 'text-info'],
                ['Exits', '▼ on signal', 'text-ink'],
                ['Costs', 'commission + slippage', 'text-muted'],
              ].map(([k, v, tone], i) => (
                <div key={k} className={`flex flex-col gap-1 px-[18px] py-3.5 ${i ? 'border-l border-line' : ''}`}>
                  <span className="text-[11px] text-subtle">{k}</span>
                  <span className={`font-mono text-[13px] font-medium ${tone}`}>{v}</span>
                </div>
              ))}
            </div>
          </figure>
        </section>

        <section aria-label="Capabilities" className="border-y border-line">
          <div className="mx-auto grid max-w-[1240px] grid-cols-[repeat(auto-fit,minmax(min(220px,100%),1fr))] px-8 max-md:px-4">
            {STATS.map((s) => (
              <div key={s.label} className="flex flex-col gap-1.5 py-8 pr-6">
                <span className="font-mono text-4xl font-bold tracking-[-0.03em]">{s.n}</span>
                <span className="text-[13px] text-subtle">{s.label}</span>
              </div>
            ))}
          </div>
        </section>

        <section id="how" aria-label="How it works" className="mx-auto flex max-w-[1240px] scroll-mt-6 flex-col gap-10 px-8 pt-24 max-md:px-4">
          <h2 className="m-0 text-[32px] font-semibold tracking-[-0.02em]">From idea to equity curve in three steps</h2>
          <ol className="m-0 grid list-none grid-cols-[repeat(auto-fit,minmax(min(300px,100%),1fr))] gap-5 p-0">
            {STEPS.map((s) => (
              <li key={s.n} className="flex flex-col gap-3 rounded-xl border border-line bg-panel p-7">
                <span className="font-mono text-[13px] font-semibold text-gain">{s.n}</span>
                <h3 className="m-0 text-xl font-semibold">{s.title}</h3>
                <p className="m-0 text-sm leading-relaxed text-muted">{s.body}</p>
              </li>
            ))}
          </ol>
        </section>

        <section id="builder" aria-label="Strategy builder" className="mx-auto flex max-w-[1240px] scroll-mt-6 flex-col gap-10 px-8 pt-28 max-md:px-4">
          <div className="flex max-w-[640px] flex-col gap-3">
            <h2 className="m-0 text-[32px] font-semibold tracking-[-0.02em]">Every rule is a block. Every block is JSON.</h2>
            <p className="m-0 text-[15px] leading-relaxed text-muted">
              Nest AND and OR groups as deep as you need. Compare indicators, prices and fixed values with eight operators, including crosses_above and
              crosses_below.
            </p>
          </div>
          <div className="flex flex-wrap items-stretch gap-6">
            <div className="flex min-w-0 flex-[1_1_480px] flex-col gap-4 rounded-xl border border-line bg-panel p-7">
              <span className="font-mono text-[13px] font-medium text-subtle">long_entry</span>
              <RuleTree node={SAMPLE.long_entry!} />
              <Link to="/login?mode=register" className="mt-2 self-start text-sm font-semibold text-info hover:underline">
                Open the builder →
              </Link>
            </div>
            <pre className="m-0 min-w-0 flex-[1_1_400px] overflow-auto rounded-xl border border-line bg-raised p-6 font-mono text-xs leading-relaxed text-ink-2">
              {JSON.stringify(canonicalJson(SAMPLE), null, 2)}
            </pre>
          </div>
        </section>

        <section id="catalog" aria-label="Indicators and operators" className="mx-auto flex max-w-[1240px] scroll-mt-6 flex-col gap-10 px-8 pt-28 max-md:px-4">
          <div className="flex max-w-[640px] flex-col gap-3">
            <h2 className="m-0 text-[32px] font-semibold tracking-[-0.02em]">24 indicators, ready to compare</h2>
            <p className="m-0 text-[15px] leading-relaxed text-muted">Each one takes its own parameters, with sensible defaults and limits.</p>
          </div>
          <div className="grid grid-cols-[repeat(auto-fit,minmax(min(260px,100%),1fr))] gap-4">
            {catalog.map(([name, codes]) => (
              <div key={name} className="flex flex-col gap-3.5 rounded-xl border border-line bg-panel p-5">
                <h3 className="m-0 text-[13px] font-semibold text-subtle">{name}</h3>
                <div className="flex flex-wrap gap-2">
                  {codes.map((code) => (
                    <span key={code} className="rounded-full border border-line-strong px-2.5 py-1.5 font-mono text-xs text-info">
                      {code}
                    </span>
                  ))}
                </div>
              </div>
            ))}
            <div className="flex flex-col gap-3.5 rounded-xl border border-line bg-panel p-5">
              <h3 className="m-0 text-[13px] font-semibold text-subtle">Operators</h3>
              <div className="flex flex-wrap gap-2">
                {OPERATORS.map((op) => (
                  <span key={op} className="rounded-full border border-gain/60 px-2.5 py-1.5 font-mono text-xs text-gain">
                    {op}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </section>

        <section aria-label="Get started" className="mx-auto max-w-[1240px] px-8 pt-[120px] pb-24 max-md:px-4">
          <div className="flex flex-wrap items-center justify-between gap-6 rounded-xl border border-line bg-panel p-10 max-md:p-6">
            <div className="flex max-w-[560px] flex-col gap-2.5">
              <h2 className="m-0 text-[32px] font-semibold tracking-[-0.02em]">
                Run your first backtest <span className="animate-[blink_1s_steps(1)_infinite] text-gain motion-reduce:animate-none">▍</span>
              </h2>
              <p className="m-0 text-[15px] leading-relaxed text-muted">Create an account, compose a rule set, press run.</p>
            </div>
            <Link to="/login?mode=register" className={buttonClass('primary', 'md', 'h-[52px] px-6 text-[15px]')}>
              Create account →
            </Link>
          </div>
        </section>
      </main>

      <footer className="border-t border-line">
        <div className="mx-auto flex max-w-[1240px] flex-wrap justify-between gap-3 px-8 py-7 text-[13px] text-subtle max-md:px-4">
          <span>Backtester</span>
          <span>Strategies are JSON · Results are reproducible</span>
        </div>
      </footer>
    </div>
  )
}
