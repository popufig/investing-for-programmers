import { useEffect, useMemo, useState } from 'react'
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, Legend } from 'recharts'
import { getGoogleTrends } from '../api/client'
import { fmtNumber } from '../utils/format'

const COMPARE_COLORS = ['#3b82f6', '#22c55e', '#f59e0b', '#a78bfa', '#ef4444']
const TIMEFRAMES = ['today 3-m', 'today 12-m', 'today 5-y']

const DEFAULT_LIDAR_KEYWORDS = {
  AEVA: ['Aeva', 'Luminar Technologies', 'Innoviz', 'Ouster'],
  LAZR: ['Luminar Technologies', 'Aeva', 'Innoviz', 'Ouster'],
  INVZ: ['Innoviz', 'Luminar Technologies', 'Aeva', 'Ouster'],
  OUST: ['Ouster', 'Luminar Technologies', 'Aeva', 'Innoviz'],
}

function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div className="card !p-2 text-xs">
      <p className="text-slate-400 mb-1">{label}</p>
      {payload.map((item) => (
        <p key={item.dataKey} style={{ color: item.color }}>
          {item.name}: {fmtNumber(item.value, 0)}
        </p>
      ))}
    </div>
  )
}

function inferDefaults(ticker, companyName) {
  const key = (ticker || '').toUpperCase()
  if (DEFAULT_LIDAR_KEYWORDS[key]) {
    return DEFAULT_LIDAR_KEYWORDS[key].slice(0, 5)
  }
  const primary = (companyName || ticker || '').trim()
  if (!primary) return []
  return [primary]
}

export default function GoogleTrends({ ticker, companyName }) {
  const [keywordsInput, setKeywordsInput] = useState('')
  const [timeframe, setTimeframe] = useState('today 12-m')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [data, setData] = useState(null)

  const runFetch = async (rawKeywords = keywordsInput, rawTimeframe = timeframe) => {
    const keywords = rawKeywords
      .split(',')
      .map((k) => k.trim())
      .filter(Boolean)
      .slice(0, 5)

    if (keywords.length === 0) {
      setError('Please enter at least one keyword')
      setData(null)
      return
    }

    setLoading(true)
    setError('')
    try {
      const res = await getGoogleTrends(keywords.join(','), rawTimeframe)
      setData(res.data)
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to load Google Trends')
      setData(null)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    const defaults = inferDefaults(ticker, companyName)
    if (defaults.length === 0) return
    const text = defaults.join(', ')
    setKeywordsInput(text)
    runFetch(text, timeframe)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ticker, companyName])

  const rows = useMemo(() => data?.data || [], [data])
  const activeKeywords = data?.keywords || []

  return (
    <div className="card">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
        <p className="card-title !mb-0">Google Trends</p>
        <div className="flex gap-2 items-center">
          <select
            value={timeframe}
            onChange={(e) => setTimeframe(e.target.value)}
            className="input !py-1.5 !px-2 text-xs w-[140px]"
          >
            {TIMEFRAMES.map((tf) => (
              <option key={tf} value={tf}>{tf}</option>
            ))}
          </select>
          <button className="btn-primary !py-1.5" onClick={() => runFetch()} disabled={loading}>
            {loading ? 'Loading…' : 'Refresh'}
          </button>
        </div>
      </div>

      <div className="mb-3">
        <input
          className="input"
          value={keywordsInput}
          onChange={(e) => setKeywordsInput(e.target.value)}
          placeholder="Keywords, comma separated (max 5)"
        />
      </div>

      {error && <p className="text-sm text-red-400">{error}</p>}
      {!error && data?.message && rows.length === 0 && <p className="text-sm text-slate-500">{data.message}</p>}

      {!error && rows.length > 0 && (
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={rows} margin={{ top: 5, right: 10, left: 8, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
            <XAxis dataKey="date" tick={{ fill: '#64748b', fontSize: 10 }} tickFormatter={(d) => d.slice(2)} />
            <YAxis tick={{ fill: '#64748b', fontSize: 10 }} width={45} domain={[0, 100]} />
            <Tooltip content={<ChartTooltip />} />
            <Legend />
            {activeKeywords.map((keyword, idx) => (
              <Line
                key={keyword}
                type="monotone"
                dataKey={keyword}
                stroke={COMPARE_COLORS[idx % COMPARE_COLORS.length]}
                dot={false}
                strokeWidth={2}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  )
}
