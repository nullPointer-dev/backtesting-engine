// Number, money and date formatting used across screens (Indian grouping, ₹).
// Dates are shown in IST: NSE bars are stamped at midnight India time.

const MINUS = '−'

export function signed(value: number | null | undefined, digits = 2, suffix = '') {
  if (value == null || !Number.isFinite(value)) return '—'
  const sign = value > 0 ? '+' : value < 0 ? MINUS : ''
  return sign + Math.abs(value).toLocaleString('en-IN', { minimumFractionDigits: digits, maximumFractionDigits: digits }) + suffix
}

export function pct(value: number | null | undefined, digits = 2) {
  return signed(value, digits, '%')
}

export function num(value: number | null | undefined, digits = 2) {
  if (value == null || !Number.isFinite(value)) return '—'
  const text = Math.abs(value).toLocaleString('en-IN', { minimumFractionDigits: digits, maximumFractionDigits: digits })
  return value < 0 ? MINUS + text : text
}

export function rupee(value: number | null | undefined, digits = 0) {
  if (value == null || !Number.isFinite(value)) return '—'
  return (value < 0 ? MINUS : '') + '₹' + Math.abs(value).toLocaleString('en-IN', { minimumFractionDigits: digits, maximumFractionDigits: digits })
}

export function signedRupee(value: number | null | undefined, digits = 0) {
  if (value == null || !Number.isFinite(value)) return '—'
  return (value > 0 ? '+' : '') + rupee(value, digits)
}

/** Colour class for a signed value. */
export function toneClass(value: number | null | undefined) {
  if (value == null || !Number.isFinite(value) || value === 0) return 'text-ink'
  return value > 0 ? 'text-gain' : 'text-loss'
}

const monthYear = new Intl.DateTimeFormat('en-GB', { month: 'short', year: 'numeric', timeZone: 'Asia/Kolkata' })
const dayMonthYear = new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'Asia/Kolkata' })
const dateTime = new Intl.DateTimeFormat('en-GB', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit', hour12: false, timeZone: 'Asia/Kolkata' })

export function monthRange(start: string, end: string) {
  const a = monthYear.format(new Date(start))
  const b = monthYear.format(new Date(end))
  return a === b ? a : `${a} – ${b}`
}

export function day(value: string | null | undefined) {
  return value ? dayMonthYear.format(new Date(value)) : '—'
}

export function dayRange(start: string, end: string) {
  return `${day(start)} → ${day(end)}`
}

export function stamp(value: string | null | undefined) {
  return value ? dateTime.format(new Date(value)) : '—'
}

export function plural(count: number, one: string, many = `${one}s`) {
  return `${count.toLocaleString('en-IN')} ${count === 1 ? one : many}`
}
