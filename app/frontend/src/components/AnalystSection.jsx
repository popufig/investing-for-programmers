import { useEffect, useMemo, useState } from 'react'
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts'
import { getAnalystData } from '../api/client'
import { fmtCurrency, fmtNumber, fmtPct } from '../utils/format'

function DistTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div className="card !p-2 text-xs">
      <p className="text-slate-400">{label}</p>
      <p className="text-slate-200">Analysts: {payload[0].value}</p>
    </div>
  )
}

const DIST_LABELS = [
  { key: 'strong_buy', label: 'Strong Buy' },
  { key: 'buy', label: 'Buy' },
  { key: 'hold', label: 'Hold' },
  { key: 'sell', label: 'Sell' },
  { key: 'strong_sell', label: 'Strong Sell' },
]

export default function AnalystSection({ ticker }) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [data, setData] = useState(null)

  useEffect(() => {
    if (!ticker) return
    let ignore = false

    const run = async () => {
      setLoading(true)
      setError('')
      try {
        const res = await getAnalystData(ticker)
        if (!ignore) setData(res.data)
      } catch (e) {
        if (!ignore) {
          setError(e.response?.data?.detail || 'Failed to load analyst data')
          setData(null)
        }
      } finally {
        if (!ignore) setLoading(false)
      }
    }

    run()
    return () => { ignore = true }
  }, [ticker])

  const distData = useMemo(() => {
    if (!data?.rating_distribution) return []
    return DIST_LABELS.map((item) => ({
      label: item.label,
      value: data.rating_distribution[item.key] ?? 0,
    }))
  }, [data])

  const hasDistribution = distData.some((d) => d.value > 0)
  const mean = data?.recommendation_mean
  const meanPct = mean != null ? Math.min(100, Math.max(0, ((mean - 1) / 4) * 100)) : 0

  const targetMin = [data?.target_low, data?.target_mean, data?.target_high, data?.current_price]
    .filter((v) => typeof v === 'number' && Number.isFinite(v))
    .reduce((acc, v) => Math.min(acc, v), Number.POSITIVE_INFINITY)

  const targetMax = [data?.target_low, data?.target_mean, data?.target_high, data?.current_price]
    .filter((v) => typeof v === 'number' && Number.isFinite(v))
    .reduce((acc, v) => Math.max(acc, v), Number.NEGATIVE_INFINITY)

  const toPct = (value) => {
    if (!Number.isFinite(value) || !Number.isFinite(targetMin) || !Number.isFinite(targetMax) || targetMax === targetMin) {
      return null
    }
    return ((value - targetMin) / (targetMax - targetMin)) * 100
  }

  return (
    <div className="card">
      <p className="card-title">Analyst Ratings</p>

      {loading && <p className="text-sm text-slate-500">Loading analyst data…</p>}
      {!loading && error && <p className="text-sm text-red-400">{error}</p>}

      {!loading && !error && data && (
        <div className="space-y-4">
          {hasDistribution ? (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={distData} margin={{ top: 5, right: 8, left: 8, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="label" tick={{ fill: '#64748b', fontSize: 10 }} />
                <YAxis tick={{ fill: '#64748b', fontSize: 10 }} width={34} />
                <Tooltip content={<DistTooltip />} />
                <Bar dataKey="value" fill="#3b82f6" />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-xs text-slate-500">Rating distribution is not available for this ticker.</p>
          )}

          <div>
            <div className="flex items-center justify-between text-xs mb-1">
              <span className="text-slate-500">Recommendation Mean (1 = Strong Buy, 5 = Strong Sell)</span>
              <span className="text-slate-200 font-medium">{fmtNumber(mean, 2)}</span>
            </div>
            <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
              <div className="h-full bg-blue-500" style={{ width: `${meanPct}%` }} />
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between text-xs mb-1">
              <span className="text-slate-500">Target Range</span>
              <span className="text-slate-400">
                Upside: {data.upside_pct != null ? fmtPct(data.upside_pct, 1) : '—'}
              </span>
            </div>
            {Number.isFinite(targetMin) && Number.isFinite(targetMax) && targetMax > targetMin ? (
              <div className="relative h-9 rounded bg-slate-800 border border-slate-700">
                <div className="absolute top-1/2 left-2 right-2 -translate-y-1/2 h-1 bg-slate-600 rounded" />
                {[
                  { label: 'Low', value: data.target_low, color: '#ef4444' },
                  { label: 'Mean', value: data.target_mean, color: '#f59e0b' },
                  { label: 'High', value: data.target_high, color: '#22c55e' },
                  { label: 'Now', value: data.current_price, color: '#3b82f6' },
                ].map((item) => {
                  const left = toPct(item.value)
                  if (left == null) return null
                  return (
                    <div key={item.label} className="absolute top-1/2 -translate-y-1/2" style={{ left: `${left}%` }}>
                      <div className="w-2 h-2 rounded-full border border-slate-900" style={{ background: item.color }} />
                      <div className="text-[10px] text-slate-400 mt-1 -translate-x-1/2 whitespace-nowrap">
                        {item.label}: {fmtCurrency(item.value)}
                      </div>
                    </div>
                  )
                })}
              </div>
            ) : (
              <p className="text-xs text-slate-500">Target range data is not available.</p>
            )}
          </div>

          <div>
            <p className="text-xs text-slate-500 mb-2">Recent Changes</p>
            <div className="overflow-x-auto">
              <table className="w-full text-xs min-w-[620px]">
                <thead>
                  <tr className="border-b border-slate-700">
                    <th className="th">Date</th>
                    <th className="th">Firm</th>
                    <th className="th">From</th>
                    <th className="th">To</th>
                    <th className="th">Action</th>
                    <th className="th text-right">Target</th>
                  </tr>
                </thead>
                <tbody>
                  {(data.recent_changes || []).slice(0, 10).map((row, i) => (
                    <tr key={`${row.date || 'd'}-${row.firm || 'f'}-${i}`} className="table-row">
                      <td className="td text-slate-400">{row.date || '—'}</td>
                      <td className="td">{row.firm || '—'}</td>
                      <td className="td">{row.from_grade || '—'}</td>
                      <td className="td">{row.to_grade || '—'}</td>
                      <td className="td">{row.action || '—'}</td>
                      <td className="td text-right">{fmtCurrency(row.price_target)}</td>
                    </tr>
                  ))}
                  {(!data.recent_changes || data.recent_changes.length === 0) && (
                    <tr>
                      <td colSpan={6} className="td text-center text-slate-500 py-6">No recent rating changes.</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
