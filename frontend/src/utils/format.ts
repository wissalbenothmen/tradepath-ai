/**
 * Format utilities for TradePath AI
 */

/** Format a number as en-US currency: $58,054.50 */
export function formatUSD(value: number | null | undefined): string {
  if (value == null) return '—'
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value)
}

/** Format a number as en-US with commas, no decimals: 58,054 */
export function formatNumber(value: number | null | undefined): string {
  if (value == null) return '—'
  return new Intl.NumberFormat('en-US').format(value)
}

/** Format a percentage: 0.875 → "87.5%" */
export function formatPct(value: number | null | undefined, decimals = 1): string {
  if (value == null) return '—'
  return `${(value * 100).toFixed(decimals)}%`
}

/** Convert snake_case / kebab-case → Title Case label */
export function formatLabel(key: string): string {
  return key
    .replace(/[_-]/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase())
}

/** Format an HS code: "847130" → "8471.30" */
export function formatHSCode(code: string | null | undefined): string {
  if (!code) return '—'
  if (code === '000000') return 'Pending'
  const clean = code.replace(/\D/g, '')
  if (clean.length === 6) return `${clean.slice(0, 4)}.${clean.slice(4)}`
  if (clean.length >= 8) return `${clean.slice(0, 4)}.${clean.slice(4, 6)}.${clean.slice(6)}`
  return code
}
