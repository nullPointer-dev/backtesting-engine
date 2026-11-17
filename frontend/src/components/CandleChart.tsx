import { CandlestickSeries, ColorType, CrosshairMode, HistogramSeries, LineStyle, createChart, type UTCTimestamp } from 'lightweight-charts'
import { useEffect, useRef } from 'react'

export interface Candle {
  datetime: string
  open: number
  high: number
  low: number
  close: number
  volume: number
}

const IST_OFFSET_S = 5.5 * 3600

/** Candlesticks with volume underneath; the axis reads in IST. */
export function CandleChart({ bars, height = 400, intraday }: { bars: Candle[]; height?: number; intraday: boolean }) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!ref.current || !bars.length) return
    const chart = createChart(ref.current, {
      autoSize: true,
      layout: {
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor: '#8e8e96',
        fontFamily: '"JetBrains Mono", ui-monospace, monospace',
        fontSize: 12,
        attributionLogo: false,
      },
      grid: { vertLines: { color: '#19191c' }, horzLines: { color: '#19191c' } },
      rightPriceScale: { borderColor: '#212126', scaleMargins: { top: 0.06, bottom: 0.24 } },
      timeScale: { borderColor: '#212126', timeVisible: intraday, secondsVisible: false },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: { color: 'rgba(242,242,244,0.45)', style: LineStyle.Dashed, labelBackgroundColor: '#19191c' },
        horzLine: { color: 'rgba(242,242,244,0.45)', style: LineStyle.Dashed, labelBackgroundColor: '#19191c' },
      },
    })
    const time = (iso: string) => (Math.floor(Date.parse(iso) / 1000) + IST_OFFSET_S) as UTCTimestamp
    const candles = chart.addSeries(CandlestickSeries, {
      upColor: '#2ebd85',
      downColor: '#f0544f',
      wickUpColor: '#2ebd85',
      wickDownColor: '#f0544f',
      borderVisible: false,
    })
    candles.setData(bars.map((b) => ({ time: time(b.datetime), open: b.open, high: b.high, low: b.low, close: b.close })))
    const volume = chart.addSeries(HistogramSeries, { priceScaleId: 'volume', priceFormat: { type: 'volume' }, lastValueVisible: false, priceLineVisible: false })
    chart.priceScale('volume').applyOptions({ scaleMargins: { top: 0.8, bottom: 0 } })
    volume.setData(
      bars.map((b) => ({ time: time(b.datetime), value: b.volume, color: b.close >= b.open ? 'rgba(46,189,133,0.45)' : 'rgba(240,84,79,0.45)' })),
    )
    chart.timeScale().fitContent()
    return () => chart.remove()
  }, [bars, intraday])

  return <div ref={ref} style={{ height }} role="img" aria-label="Price and volume chart" />
}
