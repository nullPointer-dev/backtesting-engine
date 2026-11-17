// The strategy JSON format (mirrors backend/app/strategy_engine/schemas) and helpers to describe it.

export type Operand =
  | { type: 'indicator'; indicator: string; params: Record<string, number | ''> }
  | { type: 'price'; field: 'open' | 'high' | 'low' | 'close' | 'volume' }
  | { type: 'value'; value: number | '' }

export type Condition = { type: 'condition'; left: Operand; operator: string; right: Operand }
export type Group = { type: 'group'; operator: 'AND' | 'OR'; children: RuleNode[] }
export type RuleNode = Condition | Group

export const RULE_KEYS = ['long_entry', 'long_exit', 'short_entry', 'short_exit'] as const
export type RuleKey = (typeof RULE_KEYS)[number]
export type StrategyJson = Partial<Record<RuleKey, RuleNode | null>>

export function operandText(o: Operand): string {
  if (o.type === 'price') return o.field
  if (o.type === 'value') return String(o.value)
  const values = Object.values(o.params ?? {})
  return values.length ? `${o.indicator}(${values.join(', ')})` : o.indicator
}

export function describe(node: RuleNode | null | undefined): string {
  if (!node) return '—'
  if (node.type === 'condition') return `${operandText(node.left)} ${node.operator} ${operandText(node.right)}`
  const parts = node.children.map(describe)
  return parts.length === 1 ? parts[0] : `(${parts.join(` ${node.operator} `)})`
}

function walk(node: RuleNode | null | undefined, visit: (c: Condition) => void) {
  if (!node) return
  if (node.type === 'group') node.children.forEach((child) => walk(child, visit))
  else visit(node)
}

export function summarize(json: StrategyJson) {
  const indicators = new Set<string>()
  let conditions = 0
  for (const key of RULE_KEYS) {
    walk(json[key], (c) => {
      conditions++
      for (const o of [c.left, c.right]) if (o.type === 'indicator') indicators.add(o.indicator)
    })
  }
  const hasShort = !!json.short_entry
  return { indicators: [...indicators], conditions, hasShort, sides: hasShort ? 'LONG + SHORT' : 'LONG' }
}

/** Rebuild a node with keys in reading order (Postgres JSONB stores them sorted by length). */
export function canonical(node: RuleNode): RuleNode {
  if (node.type === 'group') return { type: 'group', operator: node.operator, children: node.children.map(canonical) }
  return { type: 'condition', left: canonicalOperand(node.left), operator: node.operator, right: canonicalOperand(node.right) }
}

function canonicalOperand(o: Operand): Operand {
  if (o.type === 'indicator') return { type: 'indicator', indicator: o.indicator, params: { ...o.params } }
  if (o.type === 'price') return { type: 'price', field: o.field }
  return { type: 'value', value: o.value }
}

export function canonicalJson(json: StrategyJson): Record<string, RuleNode> {
  const out: Record<string, RuleNode> = {}
  for (const key of RULE_KEYS) if (json[key]) out[key] = canonical(json[key]!)
  return out
}
