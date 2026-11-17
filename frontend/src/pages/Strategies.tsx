import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, unwrap } from '../api/client'
import { useDeleteStrategy, useStrategies, type Strategy } from '../api/queries'
import { PlusIcon, TrashIcon } from '../components/icons'
import { Button, ButtonLink, Card, EmptyState, ErrorNote, IconButton, Loading, PageHeader } from '../components/ui'
import { day, plural } from '../lib/format'
import { canonicalJson, describe, summarize, type StrategyJson } from '../lib/strategy'
import { inputClass, labelClass } from '../lib/styles'

function StrategyCard({ strategy }: { strategy: Strategy }) {
  const json = strategy.strategy_json as StrategyJson
  const info = summarize(json)
  const [open, setOpen] = useState(false)
  const [confirming, setConfirming] = useState<null | { backtests: number }>(null)
  const remove = useDeleteStrategy()

  async function askDelete() {
    // Deleting a strategy also deletes its backtests, so say how many.
    const { total } = await unwrap(
      api.GET('/backtests', { params: { query: { strategy_id: strategy.strategy_id, limit: 1 } } }),
    ).catch(() => ({ total: 0 }))
    setConfirming({ backtests: total })
  }

  return (
    <Card as="article" className="flex flex-col gap-4 px-6 py-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex min-w-0 flex-[1_1_360px] flex-col gap-2.5">
          <div className="flex flex-wrap items-center gap-3">
            <Link to={`/strategies/${strategy.strategy_id}`} className="text-[17px] font-semibold hover:underline">
              {strategy.name}
            </Link>
            <span
              className={`rounded-full px-2 py-0.5 font-mono text-[11px] font-semibold ${
                info.hasShort ? 'bg-violet/16 text-violet' : 'bg-info/14 text-info'
              }`}
            >
              {info.sides}
            </span>
          </div>
          <div className="flex flex-col gap-1 text-xs break-words text-muted">
            <span>
              <span className="font-mono text-subtle">long_entry</span>&nbsp; {describe(json.long_entry)}
            </span>
            <span>
              <span className="font-mono text-subtle">long_exit</span>&nbsp;&nbsp; {describe(json.long_exit)}
            </span>
            {info.hasShort && (
              <>
                <span>
                  <span className="font-mono text-subtle">short_entry</span> {describe(json.short_entry)}
                </span>
                <span>
                  <span className="font-mono text-subtle">short_exit</span>&nbsp; {describe(json.short_exit)}
                </span>
              </>
            )}
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {info.indicators.map((code) => (
              <span
                key={code}
                className="rounded-full border border-line-strong bg-canvas px-2 py-1 font-mono text-[11px] font-semibold text-info"
              >
                {code}
              </span>
            ))}
            <span className="font-mono text-[13px] text-subtle">{plural(info.conditions, 'condition')}</span>
          </div>
        </div>

        <div className="flex flex-col items-end gap-3">
          <span className="text-right text-[13px] text-subtle">
            Created {day(strategy.created_at)}
            <br />
            Updated {day(strategy.updated_at)}
          </span>
          {confirming ? (
            <div
              role="alertdialog"
              aria-label="Confirm delete"
              className="flex flex-wrap items-center justify-end gap-2.5 rounded-xl border border-loss bg-loss/10 px-3 py-2"
            >
              <span className="text-[13px] text-loss-soft">
                {confirming.backtests
                  ? `Delete this strategy and its ${plural(confirming.backtests, 'backtest')}?`
                  : 'Delete this strategy?'}
              </span>
              <Button variant="danger" size="xs" disabled={remove.isPending} onClick={() => remove.mutate(strategy.strategy_id)}>
                {remove.isPending ? 'Deleting…' : 'Delete'}
              </Button>
              <Button variant="secondary" size="xs" onClick={() => setConfirming(null)}>
                Keep
              </Button>
            </div>
          ) : (
            <div className="flex flex-wrap justify-end gap-2">
              <ButtonLink variant="accent" size="sm" to={`/backtests/new?strategy=${strategy.strategy_id}`}>
                Backtest
              </ButtonLink>
              <Button variant="secondary" size="sm" aria-expanded={open} onClick={() => setOpen(!open)}>
                {open ? 'Hide JSON' : 'View JSON'}
              </Button>
              <ButtonLink variant="secondary" size="sm" to={`/strategies/${strategy.strategy_id}`}>
                Edit
              </ButtonLink>
              <IconButton label="Delete strategy" tone="danger" onClick={askDelete}>
                <TrashIcon />
              </IconButton>
            </div>
          )}
          {remove.error && <ErrorNote messages={[remove.error.message]} />}
        </div>
      </div>
      {open && (
        <pre className="m-0 max-h-[360px] overflow-auto rounded-xl bg-canvas p-4 font-mono text-xs leading-relaxed text-ink-2">
          {JSON.stringify(canonicalJson(json), null, 2)}
        </pre>
      )}
    </Card>
  )
}

export function Strategies() {
  const strategies = useStrategies()
  const [query, setQuery] = useState('')
  const all = useMemo(() => strategies.data?.strategies ?? [], [strategies.data])
  const shown = useMemo(() => {
    const q = query.trim().toLowerCase()
    return q ? all.filter((s) => s.name.toLowerCase().includes(q)) : all
  }, [all, query])

  return (
    <>
      <PageHeader
        title="Strategies"
        subtitle={strategies.data ? plural(strategies.data.total, 'saved strategy', 'saved strategies') : ' '}
        actions={
          <ButtonLink to="/strategies/new">
            <PlusIcon /> New strategy
          </ButtonLink>
        }
      />

      {all.length > 0 && (
        <div className="flex max-w-[420px] flex-col gap-2">
          <label htmlFor="q" className={labelClass}>
            Search by name
          </label>
          <input
            id="q"
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="RSI, crossover…"
            className={`${inputClass} bg-panel`}
          />
        </div>
      )}

      {strategies.isPending ? (
        <Loading />
      ) : strategies.error ? (
        <ErrorNote messages={[strategies.error.message]} />
      ) : all.length === 0 ? (
        <EmptyState action={<ButtonLink to="/strategies/new">New strategy</ButtonLink>}>
          No strategies yet. Build entry and exit rules from indicators, prices and values.
        </EmptyState>
      ) : shown.length === 0 ? (
        <EmptyState>No strategies match this search.</EmptyState>
      ) : (
        <div className="flex flex-col gap-3">
          {shown.map((s) => (
            <StrategyCard key={s.strategy_id} strategy={s} />
          ))}
        </div>
      )}
    </>
  )
}
