import { useEffect, useMemo, useState } from 'react'
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts'
import { getFredSeries } from '../api/client'
import { fmtNumber } from '../utils/format'

const SERIES_OPTIONS = [
  { id: 'DFF', label: 'Fed Funds' },
  { id: 'DGS10', label: '10Y Treasury' },
  { id: 'DGS2', label: '2Y Treasury' },
]

const PERIODS = ['1y', '2y', '5y', 'max']

function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div className="card !p-2 text-xs">
      <p className="text-slate-400 mb-1">{label}</p>
      <p className="text-slate-200">Rate: {fmtNumber(payload[0].value, 3)}%</p>
    </div>
  )
}

export default function FredRateChart() {
  const [seriesId, setSeriesId] = useState('DFF')
  const [period, setPeriod] = useState('5y')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [data, setData] = useState(null)

  useEffect(() => {
    let ignore = false

    const run = async () => {
      setLoading(true)
      setError('')
      try {
        const res = await getFredSeries(seriesId, period)
        if (!ignore) setData(res.data)
      } catch (e) {
        if (!ignore) {
          setError(e.response?.data?.detail || 'Failed to load FRED data')
          setData(null)
        }
      } finally {
        if (!ignore) setLoading(false)
      }
    }

    run()
    return () => { ignore = true }
  }, [seriesId, period])

  const rows = useMemo(() => data?.data || [], [data])
  const latest = rows.length > 0 ? rows[rows.length - 1] : null

  return (
    <div className="card">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
        <p className="card-title !mb-0">FRED Macro Rates</p>
        <div className="flex items-center gap-2 flex-wrap">
          <select
            value={seriesId}
            onChange={(e) => setSeriesId(e.target.value)}
            className="input !py-1.5 !px-2 text-xs w-[150px]"
          >
            {SERIES_OPTIONS.map((option) => (
              <option key={option.id} value={option.id}>{option.label}</option>
            ))}
          </select>
          {PERIODS.map((p) => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              className={`px-2.5 py-1 rounded text-xs ${period === p ? 'bg-blue-600 text-white' : 'text-slate-400 hover:bg-slate-700 hover:text-slate-200'}`}
            >
              {p}
            </button>
          ))}
        </div>
      </div>

      {loading && <p className="text-sm text-slate-500">Loading FRED data…</p>}
      {!loading && error && <p className="text-sm text-red-400">{error}</p>}
      {!loading && !error && data?.message && rows.length === 0 && (
        <p className="text-sm text-slate-500">{data.message}</p>
      )}

      {!loading && !error && rows.length > 0 && (
        <>
          <div className="text-xs text-slate-500 mb-2">
            {data?.title || seriesId}
            {latest?.value != null && (
              <span className="ml-2 text-slate-300">Current: {fmtNumber(latest.value, 3)}%</span>
            )}
          </div>
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={rows} margin={{ top: 5, right: 10, left: 8, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="date" tick={{ fill: '#64748b', fontSize: 10 }} tickFormatter={(d) => d.slice(2)} />
              <YAxis tick={{ fill: '#64748b', fontSize: 10 }} width={55} />
              <Tooltip content={<ChartTooltip />} />
              <Line type="monotone" dataKey="value" stroke="#3b82f6" strokeWidth={2} dot={false} name="Rate" />
            </LineChart>
          </ResponsiveContainer>
        </>
      )}
    </div>
  )
}
