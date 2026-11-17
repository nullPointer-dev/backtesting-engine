import type { BacktestSummary } from '../api/queries'
import { num } from './format'

export function sizingText(b: Pick<BacktestSummary, 'position_sizing_type' | 'quantity' | 'position_size_percent'>) {
  return b.position_sizing_type === 'FIXED_QUANTITY'
    ? `Fixed quantity · ${num(b.quantity ?? 0, 0)}`
    : `${num(b.position_size_percent ?? 0, 0)}% of capital`
}

/** Where a backtest row should lead: the live run screen while it runs, results otherwise. */
export function backtestHref(b: Pick<BacktestSummary, 'backtest_id' | 'status'>) {
  return b.status === 'RUNNING' ? `/backtests/${b.backtest_id}/run` : `/backtests/${b.backtest_id}`
}

/** The grey line under a strategy name in backtest tables. */
export function backtestNote(b: BacktestSummary) {
  if ((b.status === 'FAILED' || b.status === 'CANCELLED') && b.error_summary) return b.error_summary
  return sizingText(b)
}
