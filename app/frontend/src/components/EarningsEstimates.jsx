import { useEffect, useMemo, useState } from 'react'
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts'
import { getEarningsEstimates } from '../api/client'
import { fmtNumber, fmtPct } from '../utils/format'

function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div className="card !p-2 text-xs">
      <p className="text-slate-400 mb-1">{label}</p>
      {payload.map((item) => (
        <p key={item.dataKey} style={{ color: item.color }}>
          {item.name}: {fmtNumber(item.value, 4)}
        </p>
      ))}
    </div>
  )
}

function growthPct(v) {
  if (v == null || Number.isNaN(v)) return null
  return Math.abs(v) <= 1 ? v * 100 : v
}

export default function EarningsEstimates({ ticker }) {
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
        const res = await getEarningsEstimates(ticker)
        if (!ignore) setData(res.data)
      } catch (e) {
        if (!ignore) {
          setError(e.response?.data?.detail || 'Failed to load earnings estimates')
          setData(null)
        }
      } finally {
        if (!ignore) setLoading(false)
      }
    }

    run()
    return () => { ignore = true }
  }, [ticker])

  const earningsRows = useMemo(() => data?.earnings_estimates || [], [data])
  const chartRows = earningsRows
    .filter((row) => row?.avg != null || row?.years_ago_eps != null)
    .map((row) => ({
      period: row.period,
      avg: row.avg,
      prior: row.years_ago_eps,
    }))

  return (
    <div className="card">
      <p className="card-title">Earnings Estimates</p>

      {loading && <p className="text-sm text-slate-500">Loading earnings estimates…</p>}
      {!loading && error && <p className="text-sm text-red-400">{error}</p>}
      {!loading && !error && data?.error && earningsRows.length === 0 && (
        <p className="text-sm text-slate-500">{data.error}</p>
      )}

      {!loading && !error && earningsRows.length > 0 && (
        <div className="space-y-4">
          {chartRows.length > 0 && (
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={chartRows} margin={{ top: 5, right: 10, left: 8, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="period" tick={{ fill: '#64748b', fontSize: 10 }} />
                <YAxis tick={{ fill: '#64748b', fontSize: 10 }} width={60} />
                <Tooltip content={<ChartTooltip />} />
                <Line type="monotone" dataKey="avg" stroke="#3b82f6" strokeWidth={2} dot={false} name="Avg EPS" />
                <Line type="monotone" dataKey="prior" stroke="#94a3b8" strokeWidth={1.5} dot={false} name="Prior EPS" />
              </LineChart>
            </ResponsiveContainer>
          )}

          <div className="overflow-x-auto">
            <table className="w-full text-xs min-w-[740px]">
              <thead>
                <tr className="border-b border-slate-700">
                  <th className="th">Period</th>
                  <th className="th text-right">Avg</th>
                  <th className="th text-right">Low</th>
                  <th className="th text-right">High</th>
                  <th className="th text-right">Prior EPS</th>
                  <th className="th text-right">Analysts</th>
                  <th className="th text-right">Growth</th>
                </tr>
              </thead>
              <tbody>
                {earningsRows.map((row) => {
                  const growth = growthPct(row.growth)
                  const growthClass = growth == null ? 'text-slate-400' : growth >= 0 ? 'text-emerald-400' : 'text-red-400'
                  return (
                    <tr key={row.period} className="table-row">
                      <td className="td text-slate-200">{row.period}</td>
                      <td className="td text-right">{fmtNumber(row.avg, 4)}</td>
                      <td className="td text-right">{fmtNumber(row.low, 4)}</td>
                      <td className="td text-right">{fmtNumber(row.high, 4)}</td>
                      <td className="td text-right text-slate-400">{fmtNumber(row.years_ago_eps, 4)}</td>
                      <td className="td text-right text-slate-400">{row.num_analysts ?? '—'}</td>
                      <td className={`td text-right ${growthClass}`}>{fmtPct(growth, 2)}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {!loading && !error && !data?.error && earningsRows.length === 0 && (
        <p className="text-sm text-slate-500">Earnings estimates are not available for this ticker.</p>
      )}
    </div>
  )
}
