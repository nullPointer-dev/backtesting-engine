import { useId, useMemo } from 'react'

export interface Marker {
  index: number
  kind: 'entry' | 'exit'
  side: 'LONG' | 'SHORT'
}

interface Props {
  values: (number | null)[]
  height: number
  color: string
  /** Draw only the first `upTo` points (replay); defaults to all. */
  upTo?: number
  /** Faint full line behind the drawn part. */
  ghost?: boolean
  area?: boolean
  /** Horizontal reference line (e.g. starting capital). */
  baseline?: number
  markers?: Marker[]
  /** Index of a vertical scan line; hidden when undefined. */
  scan?: number
  format(value: number): string
  ticks?: number
  label: string
}

const W = 1000 // viewBox width; the SVG stretches horizontally

/**
 * Minimal responsive line chart in SVG: y-axis labels on the left, a line
 * (optionally drawn only up to an index for replays), markers and a scan line.
 */
export function LineChart({ values, height, color, upTo, ghost, area, baseline, markers = [], scan, format, ticks = 5, label }: Props) {
  const gradientId = useId()
  const finite = values.filter((v): v is number => v != null && Number.isFinite(v))
  const [lo, hi] = useMemo(() => {
    if (!finite.length) return [0, 1]
    let min = Math.min(...finite)
    let max = Math.max(...finite)
    if (baseline != null) {
      min = Math.min(min, baseline)
      max = Math.max(max, baseline)
    }
    const pad = (max - min) * 0.06 || Math.abs(max) * 0.02 || 1
    // An all-positive series (prices, equity) never gets a negative axis.
    return [min >= 0 ? Math.max(0, min - pad) : min - pad, max + pad]
  }, [finite, baseline])

  const n = values.length
  const x = (i: number) => (n <= 1 ? 0 : (i / (n - 1)) * W)
  const y = (v: number) => height - ((v - lo) / (hi - lo)) * height
  const end = Math.min(n, upTo ?? n)

  const path = (count: number) => {
    let d = ''
    let pen = false
    for (let i = 0; i < count; i++) {
      const v = values[i]
      if (v == null || !Number.isFinite(v)) {
        pen = false
        continue
      }
      d += `${pen ? 'L' : 'M'}${x(i).toFixed(2)} ${y(v).toFixed(2)}`
      pen = true
    }
    return d
  }

  const line = path(end)
  const lastIndex = (() => {
    for (let i = end - 1; i >= 0; i--) if (values[i] != null) return i
    return -1
  })()
  const areaPath = area && line && lastIndex >= 0 ? `${line}L${x(lastIndex)} ${height}L${x(0)} ${height}Z` : ''
  const tickValues = Array.from({ length: ticks }, (_, i) => hi - ((hi - lo) * i) / (ticks - 1))

  return (
    <div className="flex gap-3">
      <div className="relative w-16 shrink-0 text-right font-mono text-xs text-subtle" style={{ height }} aria-hidden="true">
        {tickValues.map((v, i) => (
          <span key={i} className="absolute right-0 -translate-y-1/2" style={{ top: `${(i / (ticks - 1)) * 100}%` }}>
            {format(v)}
          </span>
        ))}
      </div>
      <div className="relative min-w-0 flex-1 border-l border-line" style={{ height }}>
        <svg
          viewBox={`0 0 ${W} ${height}`}
          preserveAspectRatio="none"
          className="absolute inset-0 h-full w-full overflow-visible"
          role="img"
          aria-label={label}
        >
          <defs>
            <linearGradient id={gradientId} x1="0" x2="0" y1="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity="0.28" />
              <stop offset="100%" stopColor={color} stopOpacity="0" />
            </linearGradient>
          </defs>
          {tickValues.map((v, i) => (
            <line key={i} x1="0" x2={W} y1={y(v)} y2={y(v)} stroke="#19191c" strokeWidth="1" vectorEffect="non-scaling-stroke" />
          ))}
          {baseline != null && (
            <line x1="0" x2={W} y1={y(baseline)} y2={y(baseline)} stroke="#45454d" strokeDasharray="4 4" strokeWidth="1" vectorEffect="non-scaling-stroke" />
          )}
          {ghost && <path d={path(n)} fill="none" stroke={color} strokeOpacity="0.22" strokeWidth="1.5" vectorEffect="non-scaling-stroke" />}
          {areaPath && <path d={areaPath} fill={`url(#${gradientId})`} />}
          <path d={line} fill="none" stroke={color} strokeWidth="1.75" strokeLinejoin="round" vectorEffect="non-scaling-stroke" />
        </svg>
        {markers
          .filter((m) => m.index < end && values[m.index] != null)
          .map((m, i) => {
            const up = (m.kind === 'entry') === (m.side === 'LONG')
            return (
              <span
                key={i}
                aria-hidden="true"
                className={`absolute -translate-x-1/2 text-[11px] leading-none ${m.kind === 'entry' ? 'text-gain' : 'text-loss'}`}
                style={{
                  left: `${(x(m.index) / W) * 100}%`,
                  top: `${(y(values[m.index]!) / height) * 100}%`,
                  transform: `translate(-50%, ${up ? '4px' : 'calc(-100% - 4px)'})`,
                }}
              >
                {up ? '▲' : '▼'}
              </span>
            )
          })}
        {scan != null && scan >= 0 && scan < n - 1 && (
          <div className="absolute inset-y-0 w-px bg-info opacity-90" style={{ left: `${(x(scan) / W) * 100}%` }} />
        )}
      </div>
    </div>
  )
}
