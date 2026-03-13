export const fmtCurrency = (v, decimals = 2) => {
  if (v == null || isNaN(v)) return '—'
  const abs = Math.abs(v)
  if (abs >= 1e9) return `$${(v / 1e9).toFixed(2)}B`
  if (abs >= 1e6) return `$${(v / 1e6).toFixed(2)}M`
  if (abs >= 1e3) return `$${(v / 1e3).toFixed(1)}K`
  return `$${v.toFixed(decimals)}`
}

export const fmtPct = (v, decimals = 2) => {
  if (v == null || isNaN(v)) return '—'
  const sign = v > 0 ? '+' : ''
  return `${sign}${v.toFixed(decimals)}%`
}

export const fmtNumber = (v, decimals = 2) => {
  if (v == null || isNaN(v)) return '—'
  return v.toLocaleString(undefined, { minimumFractionDigits: decimals, maximumFractionDigits: decimals })
}

export const fmtMultiplier = (v) => {
  if (v == null || isNaN(v)) return '—'
  return `${v.toFixed(1)}x`
}

export const gainColor = (v) => {
  if (v == null) return 'text-slate-400'
  return v >= 0 ? 'text-emerald-400' : 'text-red-400'
}

export const assetTypeBadge = (type) => {
  const map = {
    STOCK: 'bg-blue-900/50 text-blue-300',
    ETF:   'bg-purple-900/50 text-purple-300',
    BOND:  'bg-amber-900/50 text-amber-300',
    FUND:  'bg-teal-900/50 text-teal-300',
  }
  return map[type] || 'bg-slate-700 text-slate-300'
}

export const marketCapLabel = (marketCap) => {
  if (marketCap == null || !Number.isFinite(marketCap)) return null
  if (marketCap >= 200e9) return { label: 'Mega Cap', color: 'text-purple-300 bg-purple-900/40' }
  if (marketCap >= 10e9) return { label: 'Large Cap', color: 'text-blue-300 bg-blue-900/40' }
  if (marketCap >= 2e9) return { label: 'Mid Cap', color: 'text-teal-300 bg-teal-900/40' }
  if (marketCap >= 300e6) return { label: 'Small Cap', color: 'text-amber-300 bg-amber-900/40' }
  return { label: 'Micro Cap', color: 'text-red-300 bg-red-900/40' }
}
