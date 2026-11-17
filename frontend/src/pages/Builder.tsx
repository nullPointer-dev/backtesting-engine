import { useEffect, useMemo, useState } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'
import { ApiError, api, unwrap } from '../api/client'
import { useReference, useSaveStrategy, useStrategy, type Reference } from '../api/queries'
import { Button, ButtonLink, Card, ErrorNote, Loading, PageHeader } from '../components/ui'
import {
  RULE_KEYS,
  canonicalJson,
  type Condition,
  type Group,
  type Operand,
  type RuleKey,
  type RuleNode,
  type StrategyJson,
} from '../lib/strategy'
import { chipClass, inputClass, labelClass } from '../lib/styles'

// ---------------------------------------------------------------- registry

type ParamSpec = Reference['indicators'][number]['params'][number]
type Registry = Map<string, ParamSpec[]>

const OPERATORS = ['>', '<', '>=', '<=', '==', '!=', 'crosses_above', 'crosses_below']
const PRICE_FIELDS = ['open', 'high', 'low', 'close', 'volume'] as const

function defaults(registry: Registry, name: string): Record<string, number> {
  return Object.fromEntries((registry.get(name) ?? []).map((p) => [p.name, p.default]))
}

const indicator = (name: string, params: Record<string, number>): Operand => ({ type: 'indicator', indicator: name, params })

function starterRules(): StrategyJson {
  return {
    long_entry: { type: 'condition', left: indicator('SMA', { period: 20 }), operator: 'crosses_above', right: indicator('SMA', { period: 50 }) },
    long_exit: { type: 'condition', left: indicator('SMA', { period: 20 }), operator: 'crosses_below', right: indicator('SMA', { period: 50 }) },
    short_entry: null,
    short_exit: null,
  }
}

function defaultCondition(registry: Registry): Condition {
  return {
    type: 'condition',
    left: indicator('RSI', registry.size ? defaults(registry, 'RSI') : { period: 14 }),
    operator: '<',
    right: { type: 'value', value: 30 },
  }
}

// ---------------------------------------------------------------- validation (mirrors strategy_engine/validation.py)

interface Check {
  valid: boolean
  errors: string[]
  warnings: string[]
}

function badNumber(value: unknown) {
  return value === '' || typeof value !== 'number' || Number.isNaN(value)
}

function paramProblem(spec: ParamSpec, value: unknown): string | null {
  if (badNumber(value)) return 'must be a number'
  const v = value as number
  if (spec.type === 'int' && !Number.isInteger(v)) return 'must be a whole number'
  if (spec.min != null && v < spec.min) return `must be at least ${spec.min}`
  if (spec.max != null && v > spec.max) return `must be at most ${spec.max}`
  return null
}

function checkLocally(rules: StrategyJson, registry: Registry): Check {
  const errors: string[] = []
  const warnings: string[] = []
  const operand = (o: Operand, path: string) => {
    if (o.type === 'indicator') {
      for (const spec of registry.get(o.indicator) ?? []) {
        const problem = paramProblem(spec, o.params[spec.name])
        if (problem) errors.push(`${path}.params.${spec.name}: ${problem}`)
      }
      const { fast_period: fast, slow_period: slow } = o.params
      if (typeof fast === 'number' && typeof slow === 'number' && fast >= slow) {
        warnings.push(`${path}.params: fast_period should be smaller than slow_period`)
      }
    } else if (o.type === 'value' && badNumber(o.value)) {
      errors.push(`${path}: value must be a number`)
    }
  }
  const node = (n: RuleNode, path: string) => {
    if (n.type === 'group') {
      if (!n.children.length) errors.push(`${path}.children: add at least one condition`)
      n.children.forEach((child, i) => node(child, `${path}.children.${i}`))
    } else {
      operand(n.left, `${path}.left`)
      operand(n.right, `${path}.right`)
      if (n.left.type === 'value' && n.right.type === 'value') {
        warnings.push(`${path}: compares two constant values, so it never changes`)
      }
    }
  }
  for (const key of RULE_KEYS) {
    const root = rules[key]
    if (root) node(root, key)
    else if (key === 'long_entry' || key === 'long_exit') errors.push(`${key}: required`)
  }
  if (rules.short_entry && !rules.short_exit) errors.push('short_exit: required when short_entry is set, otherwise short positions never close')
  if (rules.short_exit && !rules.short_entry) warnings.push('short_exit: ignored because there is no short_entry')
  return { valid: errors.length === 0, errors, warnings }
}

/** The JSON that is sent: empty rules are left out, keys in reading order. */
const toJson = canonicalJson

// ---------------------------------------------------------------- tree editing

type Path = number[]

function nodeAt(root: RuleNode, path: Path): RuleNode {
  return path.reduce<RuleNode>((node, i) => (node as Group).children[i], root)
}

const selectBase =
  'cursor-pointer rounded-full border border-line-strong bg-panel font-mono [color-scheme:dark] h-7 px-1.5'

function OperandEditor({
  operand,
  registry,
  onChange,
}: {
  operand: Operand
  registry: Registry
  onChange(next: Operand): void
}) {
  return (
    <div className="flex flex-wrap items-center gap-1.5 rounded-full border border-line-strong bg-canvas p-1.5">
      <select
        aria-label="Operand type"
        value={operand.type}
        onChange={(e) => {
          const t = e.target.value
          onChange(
            t === 'indicator'
              ? indicator('RSI', defaults(registry, 'RSI'))
              : t === 'price'
                ? { type: 'price', field: 'close' }
                : { type: 'value', value: 0 },
          )
        }}
        className={`${selectBase} text-[11px] text-subtle`}
      >
        <option value="indicator">indicator</option>
        <option value="price">price</option>
        <option value="value">value</option>
      </select>

      {operand.type === 'indicator' && (
        <>
          <select
            aria-label="Indicator"
            value={operand.indicator}
            onChange={(e) => onChange(indicator(e.target.value, defaults(registry, e.target.value)))}
            className={`${selectBase} text-[13px] font-semibold text-info`}
          >
            {[...registry.keys()].map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>
          {(registry.get(operand.indicator) ?? []).map((spec) => {
            const value = operand.params[spec.name]
            const bad = paramProblem(spec, value) !== null
            return (
              <label key={spec.name} className="inline-flex items-center gap-1 text-[11px] text-subtle">
                {spec.name}
                <input
                  type="number"
                  value={value ?? ''}
                  min={spec.min ?? undefined}
                  max={spec.max ?? undefined}
                  step={spec.type === 'int' ? 1 : 0.1}
                  aria-invalid={bad}
                  onChange={(e) =>
                    onChange({
                      ...operand,
                      params: { ...operand.params, [spec.name]: e.target.value === '' ? '' : Number(e.target.value) },
                    })
                  }
                  className={`h-7 w-16 rounded-full border bg-panel px-1.5 font-mono text-[13px] [color-scheme:dark] ${
                    bad ? 'border-loss' : 'border-line-strong'
                  }`}
                />
              </label>
            )
          })}
        </>
      )}

      {operand.type === 'price' && (
        <select
          aria-label="Price field"
          value={operand.field}
          onChange={(e) => onChange({ type: 'price', field: e.target.value as (typeof PRICE_FIELDS)[number] })}
          className={`${selectBase} text-[13px] font-semibold`}
        >
          {PRICE_FIELDS.map((f) => (
            <option key={f} value={f}>
              {f}
            </option>
          ))}
        </select>
      )}

      {operand.type === 'value' && (
        <input
          type="number"
          aria-label="Value"
          step="any"
          value={operand.value}
          aria-invalid={badNumber(operand.value)}
          onChange={(e) => onChange({ type: 'value', value: e.target.value === '' ? '' : Number(e.target.value) })}
          className={`h-7 w-[88px] rounded-full border bg-panel px-1.5 font-mono text-[13px] font-semibold [color-scheme:dark] ${
            badNumber(operand.value) ? 'border-loss' : 'border-line-strong'
          }`}
        />
      )}
    </div>
  )
}

const CloseIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
    <path d="M6 6l12 12M18 6L6 18" />
  </svg>
)

const roundButton =
  'inline-flex shrink-0 cursor-pointer items-center justify-center rounded-full border border-line-strong bg-panel hover:border-ink disabled:cursor-not-allowed disabled:opacity-35'

interface NodeProps {
  node: RuleNode
  path: Path
  canDelete: boolean
  registry: Registry
  edit(path: Path, fn: (node: RuleNode) => RuleNode | null): void
  addChild(path: Path, child: RuleNode): void
}

function NodeView({ node, path, canDelete, registry, edit, addChild }: NodeProps) {
  if (node.type === 'condition') {
    return (
      <div className="flex flex-wrap items-start gap-2.5 rounded-xl border border-line bg-panel-3 p-3">
        <OperandEditor operand={node.left} registry={registry} onChange={(left) => edit(path, () => ({ ...node, left }))} />
        <select
          aria-label="Operator"
          value={node.operator}
          onChange={(e) => edit(path, () => ({ ...node, operator: e.target.value }))}
          className="h-10 cursor-pointer rounded-full border border-gain bg-canvas px-2.5 font-mono text-[13px] font-semibold text-gain [color-scheme:dark]"
        >
          {OPERATORS.map((op) => (
            <option key={op} value={op}>
              {op}
            </option>
          ))}
        </select>
        <OperandEditor operand={node.right} registry={registry} onChange={(right) => edit(path, () => ({ ...node, right }))} />
        <span className="flex-1" />
        <button
          type="button"
          aria-label="Wrap in group"
          title="Wrap in group"
          onClick={() => edit(path, (n) => ({ type: 'group', operator: 'AND', children: [n] }))}
          className={`${roundButton} size-10 text-muted`}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
            <path d="M8 4H5v16h3M16 4h3v16h-3" />
          </svg>
        </button>
        <button
          type="button"
          aria-label="Delete condition"
          title="Delete condition"
          disabled={!canDelete}
          onClick={() => edit(path, () => null)}
          className={`${roundButton} size-10 text-loss`}
        >
          <CloseIcon />
        </button>
      </div>
    )
  }

  const and = node.operator === 'AND'
  const rail = and ? 'border-info' : 'border-violet'
  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap items-center gap-3 rounded-xl border border-line bg-canvas px-3 py-2">
        <div role="group" aria-label="Group operator" className="inline-flex gap-1">
          {(['AND', 'OR'] as const).map((op) => {
            const on = node.operator === op
            const tone = op === 'AND' ? 'border-info bg-info' : 'border-violet bg-violet'
            return (
              <button
                key={op}
                type="button"
                aria-pressed={on}
                onClick={() => edit(path, () => ({ ...node, operator: op }))}
                className={`h-9 min-w-14 cursor-pointer rounded-full border px-3 text-xs font-bold ${
                  on ? `${tone} text-canvas` : 'border-line-strong bg-panel text-muted hover:border-ink'
                }`}
              >
                {op}
              </button>
            )
          })}
        </div>
        <span className="font-mono text-[13px] text-muted">{and ? 'all of these must be true' : 'any of these can be true'}</span>
        <span className="flex-1" />
        <button
          type="button"
          aria-label="Delete group"
          title="Delete group"
          disabled={!canDelete}
          onClick={() => edit(path, () => null)}
          className={`${roundButton} size-9 text-loss`}
        >
          <CloseIcon />
        </button>
      </div>
      <div className={`ml-1.5 flex flex-col gap-2 border-l-2 pl-3.5 ${rail}`}>
        {node.children.map((child, i) => (
          <NodeView
            key={i}
            node={child}
            path={[...path, i]}
            canDelete={node.children.length > 1}
            registry={registry}
            edit={edit}
            addChild={addChild}
          />
        ))}
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => addChild(path, defaultCondition(registry))}
            className="h-9 cursor-pointer rounded-full border border-dashed border-line-strong px-3.5 text-xs font-semibold text-muted hover:border-ink hover:text-ink"
          >
            + Condition
          </button>
          <button
            type="button"
            onClick={() => addChild(path, { type: 'group', operator: 'AND', children: [defaultCondition(registry)] })}
            className="h-9 cursor-pointer rounded-full border border-dashed border-line-strong px-3.5 text-xs font-semibold text-muted hover:border-ink hover:text-ink"
          >
            + Group
          </button>
        </div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------- page

function useServerCheck(json: string, enabled: boolean) {
  const [result, setResult] = useState<(Check & { for: string }) | null>(null)
  useEffect(() => {
    if (!enabled) return
    const timer = setTimeout(async () => {
      try {
        const res = await unwrap(api.POST('/strategies/validate', { body: { strategy_json: JSON.parse(json) } }))
        setResult({ for: json, valid: res.valid, errors: res.errors ?? [], warnings: res.warnings ?? [] })
      } catch {
        /* the local check still shows; saving reports server errors */
      }
    }, 400)
    return () => clearTimeout(timer)
  }, [json, enabled])
  return result?.for === json ? result : null
}

export function Builder() {
  const { strategyId } = useParams()
  const editingId = strategyId ? Number(strategyId) : undefined
  const existing = useStrategy(editingId)
  const reference = useReference()
  const save = useSaveStrategy()
  const navigate = useNavigate()
  const location = useLocation()

  const registry: Registry = useMemo(
    () => new Map((reference.data?.indicators ?? []).map((i) => [i.name, i.params])),
    [reference.data],
  )

  const [name, setName] = useState(editingId ? '' : 'Untitled strategy')
  const [rules, setRules] = useState<StrategyJson>(starterRules)
  const [tab, setTab] = useState<RuleKey>('long_entry')
  const [loadedId, setLoadedId] = useState<number | undefined>(undefined)
  const [saved, setSaved] = useState<{ id: number; at: string } | null>(null)
  const [saveErrors, setSaveErrors] = useState<string[]>([])

  // Load the strategy being edited once it arrives.
  if (existing.data && loadedId !== existing.data.strategy_id) {
    const loaded: StrategyJson = { short_entry: null, short_exit: null, ...(existing.data.strategy_json as StrategyJson) }
    setLoadedId(existing.data.strategy_id)
    setName(existing.data.name)
    setRules(loaded)
    // Arrived here straight after creating it: keep showing "saved".
    if ((location.state as { saved?: boolean } | null)?.saved) {
      setSaved({ id: existing.data.strategy_id, at: JSON.stringify(toJson(loaded), null, 2) + existing.data.name })
    }
  }

  const json = useMemo(() => JSON.stringify(toJson(rules), null, 2), [rules])
  const local = useMemo(() => checkLocally(rules, registry), [rules, registry])
  const server = useServerCheck(json, registry.size > 0)
  const check = server ?? local
  const dirty = saved == null || saved.at !== json + name

  function update(fn: (draft: StrategyJson) => void) {
    setRules((prev) => {
      const next = structuredClone(prev)
      fn(next)
      return next
    })
  }

  function edit(path: Path, fn: (node: RuleNode) => RuleNode | null) {
    update((draft) => {
      const root = draft[tab]!
      if (path.length === 0) {
        draft[tab] = fn(root)
        return
      }
      const parent = nodeAt(root, path.slice(0, -1)) as Group
      const index = path[path.length - 1]
      const next = fn(parent.children[index])
      if (next) parent.children[index] = next
      else parent.children.splice(index, 1)
    })
  }

  function addChild(path: Path, child: RuleNode) {
    update((draft) => {
      ;(nodeAt(draft[tab]!, path) as Group).children.push(child)
    })
  }

  async function submit() {
    setSaveErrors([])
    try {
      const result = await save.mutateAsync({ id: editingId, name: name.trim(), strategy_json: toJson(rules) })
      setSaved({ id: result.strategy_id, at: json + name })
      if (editingId == null) navigate(`/strategies/${result.strategy_id}`, { replace: true, state: { saved: true } })
    } catch (error) {
      setSaveErrors(error instanceof ApiError ? error.messages : ['Could not save the strategy.'])
    }
  }

  if (editingId != null && existing.isPending) return <Loading label="Loading strategy…" />
  if (editingId != null && existing.error) {
    return (
      <>
        <PageHeader title="Strategy not found" breadcrumb={[{ label: 'Strategies', to: '/strategies' }]} />
        <ErrorNote messages={[existing.error.message]} />
      </>
    )
  }

  const root = rules[tab]
  const nameMissing = !name.trim()
  const status = check.valid
    ? { text: 'VALID', tone: 'bg-gain/14 text-gain' }
    : { text: `${check.errors.length} ${check.errors.length === 1 ? 'ERROR' : 'ERRORS'}`, tone: 'bg-loss/14 text-loss' }

  return (
    <>
      <PageHeader
        breadcrumb={[{ label: 'Strategies', to: '/strategies' }, { label: editingId != null ? existing.data?.name ?? '' : 'New' }]}
        title="Strategy builder"
        subtitle="Compose entry and exit rules from conditions and AND / OR groups. Rules are checked on each bar's close and orders fill at the next bar's open."
        actions={
          <>
            <span className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-semibold ${status.tone}`}>
              <span className="size-1.5 rounded-full bg-current" />
              {status.text}
            </span>
            <Button onClick={submit} disabled={!local.valid || nameMissing || save.isPending}>
              {save.isPending ? 'Saving…' : 'Save strategy'}
            </Button>
          </>
        }
      />

      {(saveErrors.length > 0 || (saved && !dirty)) && (
        <div aria-live="polite">
          {saveErrors.length > 0 ? (
            <ErrorNote title="Not saved" messages={saveErrors} />
          ) : (
            <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl bg-gain/14 px-4 py-3 text-[13px] text-gain">
              Strategy saved.
              <ButtonLink to={`/backtests/new?strategy=${saved!.id}`} variant="accent" size="xs">
                Backtest it →
              </ButtonLink>
            </div>
          )}
        </div>
      )}

      <div className="flex flex-wrap items-start gap-6">
        <section aria-label="Rule editor" className="flex min-w-0 flex-[3_1_560px] flex-col gap-5">
          <Card className="flex flex-col gap-2 px-6 py-5">
            <label htmlFor="sname" className={labelClass}>
              Strategy name
            </label>
            <input
              id="sname"
              value={name}
              maxLength={100}
              aria-invalid={nameMissing}
              onChange={(e) => setName(e.target.value)}
              className={`${inputClass} max-w-[480px]`}
            />
          </Card>

          <div role="group" aria-label="Rule" className="flex flex-wrap gap-2">
            {RULE_KEYS.map((key) => (
              <button
                key={key}
                type="button"
                aria-pressed={tab === key}
                onClick={() => setTab(key)}
                className={chipClass(tab === key, 'font-mono')}
              >
                {key}
                {!rules[key] && <span className="text-[11px] font-medium opacity-75">empty</span>}
              </button>
            ))}
          </div>

          <Card className="flex flex-col gap-1 p-6">
            {reference.isPending ? (
              <Loading label="Loading indicators…" />
            ) : !root ? (
              <div className="flex flex-col items-start gap-3.5 py-3">
                <p className="m-0 text-sm text-muted">
                  No <span className="font-mono text-ink">{tab}</span> rule.
                  {tab.startsWith('short') ? ' Without it the strategy only trades the long side.' : ' This rule is required.'}
                </p>
                <Button variant="secondary" onClick={() => update((d) => (d[tab] = defaultCondition(registry)))}>
                  Add rule
                </Button>
              </div>
            ) : (
              <NodeView
                node={root}
                path={[]}
                canDelete={tab.startsWith('short')}
                registry={registry}
                edit={edit}
                addChild={addChild}
              />
            )}
          </Card>
        </section>

        <aside className="flex min-w-0 flex-[2_1_380px] flex-col gap-6">
          <Card aria-label="Strategy JSON" className="flex flex-col gap-3.5 p-6">
            <div className="flex items-baseline justify-between gap-3">
              <h2 className="m-0 font-mono text-[15px] font-medium">strategy_json</h2>
              <button
                type="button"
                onClick={() => navigator.clipboard?.writeText(json)}
                className="cursor-pointer text-[13px] text-subtle hover:text-ink"
              >
                Copy
              </button>
            </div>
            <pre className="m-0 max-h-[560px] overflow-auto rounded-xl bg-canvas p-4 font-mono text-xs leading-relaxed text-ink-2">{json}</pre>
          </Card>

          <Card aria-label="Validation" className="flex flex-col gap-3 p-6">
            <div className="flex items-baseline justify-between gap-3">
              <h2 className="m-0 text-[15px] font-medium">Validation</h2>
              <span className="font-mono text-[13px] text-subtle">{server ? `valid: ${server.valid}` : 'checking…'}</span>
            </div>
            {check.errors.length > 0 && (
              <ul className="m-0 flex flex-col gap-1 rounded-xl bg-loss/14 py-3 pr-3 pl-7 text-[13px] text-loss-soft">
                {check.errors.map((e) => (
                  <li key={e} className="font-mono">
                    {e}
                  </li>
                ))}
              </ul>
            )}
            {check.warnings.length > 0 && (
              <ul className="m-0 flex flex-col gap-1 rounded-xl bg-info/14 py-3 pr-3 pl-7 text-[13px] text-info-soft">
                {check.warnings.map((w) => (
                  <li key={w} className="font-mono">
                    {w}
                  </li>
                ))}
              </ul>
            )}
            {check.errors.length === 0 && check.warnings.length === 0 && (
              <p className="m-0 rounded-xl bg-gain/14 p-3 text-[13px] text-gain">No errors or warnings.</p>
            )}
            {nameMissing && <p className="m-0 text-[13px] text-loss-soft">Give the strategy a name to save it.</p>}
          </Card>
          <Link to="/strategies" className="text-[13px] text-subtle hover:text-ink">
            ← Back to strategies
          </Link>
        </aside>
      </div>
    </>
  )
}
