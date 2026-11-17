import type { Trade } from '../api/queries'

/**
 * Slippage cost of one trade. Fills are stored after slippage, so the raw
 * prices are recovered from the slippage rate (see PortfolioEngine._fill_price).
 */
export function slippageCost(trade: Trade, slippagePct: number) {
  const s = slippagePct / 100
  if (!s) return 0
  const q = trade.quantity
  if (trade.side === 'LONG') {
    return q * (trade.entry_price - trade.entry_price / (1 + s)) + q * (trade.exit_price / (1 - s) - trade.exit_price)
  }
  return q * (trade.entry_price / (1 - s) - trade.entry_price) + q * (trade.exit_price - trade.exit_price / (1 + s))
}

export function costBreakdown(trades: Trade[], slippagePct: number) {
  const net = trades.reduce((sum, t) => sum + t.pnl, 0)
  const commission = trades.reduce((sum, t) => sum + (t.commission ?? 0), 0)
  const slippage = trades.reduce((sum, t) => sum + slippageCost(t, slippagePct), 0)
  const gross = net + commission + slippage
  return { gross, commission, slippage, net, share: gross > 0 ? ((commission + slippage) / gross) * 100 : null }
}

function niceStep(raw: number) {
  const power = 10 ** Math.floor(Math.log10(raw))
  for (const m of [1, 2, 2.5, 5, 10]) if (m * power >= raw) return m * power
  return 10 * power
}

/** P&L histogram with a round bucket width; buckets never straddle zero. */
export function pnlHistogram(pnls: number[], target = 8) {
  if (!pnls.length) return { width: 0, buckets: [] as { from: number; count: number }[] }
  const min = Math.min(...pnls)
  const max = Math.max(...pnls)
  const width = niceStep(Math.max(max - min, 1) / target)
  const first = Math.floor(min / width) * width
  const count = Math.max(1, Math.floor((max - first) / width) + 1)
  const buckets = Array.from({ length: count }, (_, i) => ({ from: first + i * width, count: 0 }))
  for (const p of pnls) buckets[Math.min(count - 1, Math.floor((p - first) / width))].count++
  return { width, buckets }
}

export function compactRupee(value: number) {
  const abs = Math.abs(value)
  const sign = value < 0 ? '−' : ''
  if (abs >= 1e7) return `${sign}₹${+(abs / 1e7).toFixed(1)}Cr`
  if (abs >= 1e5) return `${sign}₹${+(abs / 1e5).toFixed(1)}L`
  if (abs >= 1e3) return `${sign}₹${+(abs / 1e3).toFixed(1)}k`
  return `${sign}₹${Math.round(abs)}`
}

export function tradeStats(trades: Trade[]) {
  const wins = trades.filter((t) => t.pnl > 0)
  const losses = trades.filter((t) => t.pnl < 0)
  const avg = (list: Trade[]) => (list.length ? list.reduce((s, t) => s + t.pnl, 0) / list.length : null)
  return { wins: wins.length, losses: losses.length, avgWin: avg(wins), avgLoss: avg(losses) }
}
