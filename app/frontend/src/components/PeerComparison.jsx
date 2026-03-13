import { useEffect, useMemo, useState } from 'react'
import { getPeerGroup, getPeers, updatePeerGroup } from '../api/client'
import { fmtCurrency, fmtPct, fmtNumber } from '../utils/format'

const METRICS = [
  { key: 'market_cap', label: 'Market Cap', direction: 'neutral' },
  { key: 'pe_ratio', label: 'P/E', direction: 'low' },
  { key: 'pb_ratio', label: 'P/B', direction: 'low' },
  { key: 'roe', label: 'ROE', direction: 'high' },
  { key: 'net_margin', label: 'Net Margin', direction: 'high' },
  { key: 'revenue_growth', label: 'Revenue Growth', direction: 'high' },
  { key: 'dividend_yield', label: 'Dividend Yield', direction: 'high' },
]

function formatMetric(key, value) {
  if (value == null) return '—'
  if (key === 'market_cap') return fmtCurrency(value)
  if (['roe', 'net_margin', 'revenue_growth', 'dividend_yield'].includes(key)) {
    return fmtPct(value * 100)
  }
  return fmtNumber(value, 2)
}

export default function PeerComparison({ ticker }) {
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [saveMsg, setSaveMsg] = useState('')
  const [saving, setSaving] = useState(false)
  const [data, setData] = useState({ skipped: [], peers: [] })

  const parsePeers = (text) => {
    const seen = new Set([(ticker || '').toUpperCase()])
    const out = []
    for (const t of text.split(',').map((s) => s.trim().toUpperCase()).filter(Boolean)) {
      if (seen.has(t)) continue
      seen.add(t)
      out.push(t)
      if (out.length >= 5) break
    }
    return out
  }

  const load = async (custom = '') => {
    if (!ticker) return
    setLoading(true)
    setError('')
    try {
      const res = await getPeers(ticker, custom)
      setData({
        skipped: res.data.skipped || [],
        peers: res.data.peers || [],
      })
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to load peer comparison')
      setData({ skipped: [], peers: [] })
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    setInput('')
    setSaveMsg('')
    load('')
    getPeerGroup(ticker)
      .then((res) => {
        const peers = res.data?.peers || []
        if (peers.length > 0) setInput(peers.join(', '))
      })
      .catch(() => {})
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ticker])

  const ranking = useMemo(() => {
    const map = {}
    for (const metric of METRICS) {
      if (metric.direction === 'neutral') continue
      const nums = data.peers
        .map((row) => row[metric.key])
        .filter((v) => typeof v === 'number' && Number.isFinite(v))
      if (!nums.length) continue
      const best = metric.direction === 'high' ? Math.max(...nums) : Math.min(...nums)
      const worst = metric.direction === 'high' ? Math.min(...nums) : Math.max(...nums)
      map[metric.key] = { best, worst }
    }
    return map
  }, [data.peers])

  const metricCellClass = (metric, value) => {
    if (value == null || metric.direction === 'neutral') return 'text-slate-300'
    const range = ranking[metric.key]
    if (!range) return 'text-slate-300'
    if (value === range.best && range.best !== range.worst) return 'text-emerald-400 font-semibold'
    if (value === range.worst && range.best !== range.worst) return 'text-red-400 font-semibold'
    return 'text-slate-300'
  }

  const onSubmit = (e) => {
    e.preventDefault()
    load(input)
  }

  const onSaveDefault = async () => {
    const peers = parsePeers(input)
    setSaving(true)
    setSaveMsg('')
    try {
      await updatePeerGroup(ticker, peers)
      setSaveMsg(peers.length ? 'Default peer group saved.' : 'Default peer group cleared.')
      await load('')
    } catch (e) {
      setSaveMsg(e.response?.data?.detail || 'Failed to save default peer group.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="card">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
        <p className="card-title !mb-0">Peer Comparison</p>
        <form onSubmit={onSubmit} className="flex gap-2">
          <input
            className="input w-72"
            placeholder="MSFT, GOOGL, META"
            value={input}
            onChange={(e) => setInput(e.target.value.toUpperCase())}
          />
          <button type="submit" className="btn-primary" disabled={loading}>Compare</button>
          <button type="button" className="btn-ghost" onClick={onSaveDefault} disabled={saving}>
            {saving ? 'Saving…' : 'Save Default'}
          </button>
        </form>
      </div>

      {loading && <p className="text-sm text-slate-500">Loading peers…</p>}
      {!loading && error && <p className="text-sm text-red-400">{error}</p>}
      {!!saveMsg && <p className="text-xs text-slate-400 mb-2">{saveMsg}</p>}

      {!loading && !error && data.skipped.length > 0 && (
        <div className="mb-3 px-3 py-2 rounded border border-amber-700 bg-amber-900/30 text-xs text-amber-200">
          Skipped: {data.skipped.join(', ')}
        </div>
      )}

      {!loading && !error && (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[860px] text-xs">
            <thead>
              <tr className="border-b border-slate-700">
                <th className="th">Ticker</th>
                <th className="th">Name</th>
                {METRICS.map((metric) => <th key={metric.key} className="th text-right">{metric.label}</th>)}
              </tr>
            </thead>
            <tbody>
              {(data.peers || []).map((row) => (
                <tr key={row.ticker} className="table-row">
                  <td className="td font-mono font-semibold text-blue-400">{row.ticker}</td>
                  <td className="td text-slate-300">{row.name || '—'}</td>
                  {METRICS.map((metric) => (
                    <td key={metric.key} className={`td text-right ${metricCellClass(metric, row[metric.key])}`}>
                      {formatMetric(metric.key, row[metric.key])}
                    </td>
                  ))}
                </tr>
              ))}
              {(!data.peers || data.peers.length === 0) && (
                <tr>
                  <td className="td text-center text-slate-500 py-8" colSpan={2 + METRICS.length}>
                    No peer data available.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
