import { operandText, type Operand, type RuleNode, type StrategyJson } from '../lib/strategy'

const RISING = new Set(['>', '>=', 'crosses_above'])
const FALLING = new Set(['<', '<=', 'crosses_below'])

function operandLabel(o: Operand) {
  if (o.type !== 'indicator') return operandText(o)
  const params = Object.entries(o.params ?? {})
  return params.length ? `${o.indicator}(${params.map(([k, v]) => `${k} ${v}`).join(', ')})` : o.indicator
}

function Pill({ children, tone = 'plain' }: { children: string; tone?: 'plain' | 'up' | 'down' | 'neutral' }) {
  const tones = {
    plain: 'bg-canvas text-ink',
    up: 'bg-gain/14 text-gain',
    down: 'bg-loss/14 text-loss',
    neutral: 'bg-panel-2 text-muted',
  }
  return <span className={`rounded-full px-2.5 py-2 ${tones[tone]}`}>{children}</span>
}

export function RuleTree({ node }: { node: RuleNode }) {
  if (node.type === 'condition') {
    const tone = RISING.has(node.operator) ? 'up' : FALLING.has(node.operator) ? 'down' : 'neutral'
    return (
      <div className="flex flex-wrap items-center gap-2 font-mono text-[13px]">
        <Pill>{operandLabel(node.left)}</Pill>
        <Pill tone={tone}>{node.operator}</Pill>
        <Pill>{operandLabel(node.right)}</Pill>
      </div>
    )
  }
  const and = node.operator === 'AND'
  return (
    <div className="flex flex-col gap-2">
      <span className={`font-mono text-xs font-semibold ${and ? 'text-info' : 'text-violet'}`}>
        {and ? 'ALL of' : 'ANY of'}
      </span>
      <div className={`flex flex-col gap-2 border-l-2 pl-3 ${and ? 'border-info' : 'border-violet'}`}>
        {node.children.map((child, i) => (
          <RuleTree key={i} node={child} />
        ))}
      </div>
    </div>
  )
}

const LABELS = { long_entry: 'Long entry', long_exit: 'Long exit', short_entry: 'Short entry', short_exit: 'Short exit' } as const

export function StrategyRules({ json }: { json: StrategyJson }) {
  const keys = (Object.keys(LABELS) as (keyof typeof LABELS)[]).filter((k) => json[k])
  return (
    <div className="flex flex-col gap-4">
      {keys.map((key) => (
        <div key={key} className="flex flex-col gap-2">
          <span className="text-[13px] font-medium text-subtle">{LABELS[key]}</span>
          <RuleTree node={json[key]!} />
        </div>
      ))}
      {!json.short_entry && (
        <p className="m-0 text-[13px] text-subtle">No short entry or exit rules are defined, so every trade is long.</p>
      )}
    </div>
  )
}
