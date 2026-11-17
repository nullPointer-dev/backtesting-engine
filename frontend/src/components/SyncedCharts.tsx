import {
  AreaSeries,
  BaselineSeries,
  CandlestickSeries,
  ColorType,
  CrosshairMode,
  HistogramSeries,
  LineStyle,
  createChart,
  createSeriesMarkers,
  type IChartApi,
  type ISeriesApi,
  type SeriesMarker,
  type Time,
  type UTCTimestamp,
} from 'lightweight-charts'
import { useEffect, useRef, type ReactNode } from 'react'
import { Card } from './ui'

const IST_OFFSET_MS = 5.5 * 3600 * 1000

/** Chart time for an ISO timestamp, shifted so the axis reads in IST. */
function chartTime(iso: string): UTCTimestamp {
  return Math.floor((Date.parse(iso) + IST_OFFSET_MS) / 1000) as UTCTimestamp
}

export interface Bar {
  datetime: string
  open: number
  high: number
  low: number
  close: number
}

export interface TradeSpan {
  entry: number // bar index of the entry fill
  exit: number // bar index of the exit fill
  held: number // last bar the position was held (the exit bar for END_OF_DATA, else the bar before)
  side: 'LONG' | 'SHORT'
  win: boolean
}

interface Props {
  bars: Bar[]
  equity: (number | null)[]
  drawdown: number[]
  spans: TradeSpan[]
  capital: number
  focus: TradeSpan | null
  /** Show roughly the last `days` calendar days, or everything when null. */
  rangeDays: number | null
  onHover(index: number | null): void
  priceHeader?: ReactNode
  priceOverlay?: ReactNode
  equityHeader?: ReactNode
}

const base = {
  layout: {
    background: { type: ColorType.Solid, color: 'transparent' },
    textColor: '#8e8e96',
    fontFamily: '"JetBrains Mono", ui-monospace, monospace',
    fontSize: 12,
    attributionLogo: false,
  },
  grid: { vertLines: { color: '#19191c' }, horzLines: { color: '#19191c' } },
  rightPriceScale: { borderColor: '#212126' },
  timeScale: { borderColor: '#212126', rightOffset: 2, minBarSpacing: 0.2 },
  crosshair: {
    mode: CrosshairMode.Normal,
    vertLine: { color: 'rgba(242,242,244,0.45)', style: LineStyle.Dashed, labelBackgroundColor: '#19191c' },
    horzLine: { color: 'rgba(242,242,244,0.45)', style: LineStyle.Dashed, labelBackgroundColor: '#19191c' },
  },
  autoSize: true,
}

const rupeeAxis = (v: number) => '₹' + Math.round(v).toLocaleString('en-IN')

export function SyncedCharts({ bars, equity, drawdown, spans, capital, focus, rangeDays, onHover, priceHeader, priceOverlay, equityHeader }: Props) {
  const priceRef = useRef<HTMLDivElement>(null)
  const equityRef = useRef<HTMLDivElement>(null)
  const ddRef = useRef<HTMLDivElement>(null)
  const charts = useRef<IChartApi[]>([])
  const hoverRef = useRef(onHover)
  useEffect(() => {
    hoverRef.current = onHover
  }, [onHover])

  useEffect(() => {
    if (!priceRef.current || !equityRef.current || !ddRef.current || !bars.length) return
    const times = bars.map((b) => chartTime(b.datetime))
    const indexOf = new Map(times.map((t, i) => [t, i]))

    // Shaded bands for the bars each trade was open, green for winners and red for losers.
    const band = new Array<string | null>(bars.length).fill(null)
    for (const s of spans) {
      for (let i = Math.max(0, s.entry); i <= Math.min(bars.length - 1, s.held); i++) {
        band[i] = s.win ? 'rgba(46,189,133,0.09)' : 'rgba(240,84,79,0.09)'
      }
    }
    const bandData = times.map((time, i) => (band[i] ? { time, value: 1, color: band[i]! } : { time }))
    const addBands = (chart: IChartApi) => {
      const series = chart.addSeries(HistogramSeries, { priceScaleId: 'bands', lastValueVisible: false, priceLineVisible: false })
      chart.priceScale('bands').applyOptions({ scaleMargins: { top: 0, bottom: 0 }, visible: false })
      series.setData(bandData)
      return series
    }

    // Price
    const price = createChart(priceRef.current, base)
    addBands(price)
    const candles = price.addSeries(CandlestickSeries, {
      upColor: '#2ebd85',
      downColor: '#f0544f',
      wickUpColor: '#2ebd85',
      wickDownColor: '#f0544f',
      borderVisible: false,
    })
    candles.setData(bars.map((b, i) => ({ time: times[i], open: b.open, high: b.high, low: b.low, close: b.close })))
    const markers: SeriesMarker<Time>[] = spans
      .flatMap((s) => [
        { i: s.entry, entry: true, side: s.side },
        { i: s.exit, entry: false, side: s.side },
      ])
      .filter((m) => m.i >= 0 && m.i < bars.length)
      .map((m) => {
        const buying = m.entry === (m.side === 'LONG')
        return {
          time: times[m.i],
          position: buying ? 'belowBar' : 'aboveBar',
          shape: buying ? 'arrowUp' : 'arrowDown',
          color: m.entry ? '#2ebd85' : '#f0544f',
        } as SeriesMarker<Time>
      })
      .sort((a, b) => (a.time as number) - (b.time as number))
    createSeriesMarkers(candles, markers)

    // Equity
    const eq = createChart(equityRef.current, { ...base, localization: { priceFormatter: rupeeAxis } })
    addBands(eq)
    const eqSeries = eq.addSeries(AreaSeries, {
      lineColor: '#6aa7ff',
      topColor: 'rgba(106,167,255,0.28)',
      bottomColor: 'rgba(106,167,255,0)',
      lineWidth: 2,
      priceLineVisible: false,
    })
    eqSeries.setData(times.map((time, i) => (equity[i] != null ? { time, value: equity[i]! } : { time })))
    eqSeries.createPriceLine({ price: capital, color: '#45454d', lineStyle: LineStyle.Dashed, lineWidth: 1, axisLabelVisible: false, title: '' })

    // Drawdown
    const dd = createChart(ddRef.current, { ...base, localization: { priceFormatter: (v: number) => `${v.toFixed(1)}%` } })
    const ddSeries = dd.addSeries(BaselineSeries, {
      baseValue: { type: 'price', price: 0 },
      topLineColor: 'rgba(0,0,0,0)',
      topFillColor1: 'rgba(0,0,0,0)',
      topFillColor2: 'rgba(0,0,0,0)',
      bottomLineColor: '#f0544f',
      bottomFillColor1: 'rgba(240,84,79,0.05)',
      bottomFillColor2: 'rgba(240,84,79,0.32)',
      lineWidth: 1,
      priceLineVisible: false,
    })
    ddSeries.setData(times.map((time, i) => ({ time, value: drawdown[i] ?? 0 })))

    const all = [price, eq, dd]
    const lead: [IChartApi, ISeriesApi<'Candlestick' | 'Area' | 'Baseline'>][] = [
      [price, candles],
      [eq, eqSeries],
      [dd, ddSeries],
    ]
    charts.current = all

    // Keep zoom/scroll and the crosshair in step across the three charts.
    let syncing = false
    for (const chart of all) {
      chart.timeScale().subscribeVisibleLogicalRangeChange((range) => {
        if (syncing || !range) return
        syncing = true
        for (const other of all) if (other !== chart) other.timeScale().setVisibleLogicalRange(range)
        syncing = false
      })
    }
    lead.forEach(([chart]) => {
      chart.subscribeCrosshairMove((param) => {
        const index = param.time != null ? indexOf.get(param.time as UTCTimestamp) : undefined
        hoverRef.current(index ?? null)
        for (const [other, series] of lead) {
          if (other === chart) continue
          if (index == null) other.clearCrosshairPosition()
          else {
            const value = series === candles ? bars[index].close : series === eqSeries ? equity[index] ?? capital : drawdown[index] ?? 0
            other.setCrosshairPosition(value, times[index], series)
          }
        }
      })
    })

    price.timeScale().fitContent()
    return () => {
      all.forEach((chart) => chart.remove())
      charts.current = []
    }
  }, [bars, equity, drawdown, spans, capital])

  // Range buttons and trade focus move the shared time scale.
  useEffect(() => {
    const [price] = charts.current
    if (!price || !bars.length) return
    const scale = price.timeScale()
    if (focus) {
      const pad = Math.max(10, Math.round((focus.exit - focus.entry) * 0.6))
      scale.setVisibleLogicalRange({ from: focus.entry - pad, to: focus.exit + pad })
    } else if (rangeDays == null) {
      scale.fitContent()
    } else {
      const last = Date.parse(bars[bars.length - 1].datetime)
      const from = bars.findIndex((b) => Date.parse(b.datetime) >= last - rangeDays * 86400_000)
      scale.setVisibleLogicalRange({ from: Math.max(0, from), to: bars.length + 1 })
    }
  }, [focus, rangeDays, bars])

  return (
    <>
      <Card aria-label="Price chart" className="flex flex-col gap-4 p-6">
        {priceHeader}
        <div className="relative h-[340px]">
          <div ref={priceRef} className="absolute inset-0" />
          {priceOverlay}
        </div>
      </Card>
      <Card aria-label="Equity and drawdown" className="flex flex-col gap-4 p-6">
        {equityHeader}
        <div ref={equityRef} className="h-[300px]" />
        <div className="flex flex-col gap-3 border-t border-panel-2 pt-5">
          <h3 className="m-0 text-[15px] font-medium">Drawdown</h3>
          <div ref={ddRef} className="h-[120px]" />
        </div>
      </Card>
    </>
  )
}
