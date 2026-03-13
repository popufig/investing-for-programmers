import { useMemo, useState } from 'react'
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts'
import { compareStocks } from '../api/client'
import { fmtNumber } from '../utils/format'

const PERIODS = ['3mo', '6mo', '1y', '2y', '5y']
const COLORS = ['#3b82f6', '#22c55e', '#f59e0b', '#a78bfa', '#ef4444', '#14b8a6']

function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div className="card !p-2.5 text-xs min-w-[180px]">
      <p className="text-slate-400 mb-1">{label}</p>
      {payload.map((item) => (
        <p key={`${item.name}-${item.dataKey}`} style={{ color: item.color }}>
          {item.name}: {fmtNumber(item.value, 2)}
        </p>
      ))}
    </div>
  )
}

export default function Compare() {
  const [input, setInput] = useState('AAPL, KO, SMR')
  const [period, setPeriod] = useState('1y')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [rows, setRows] = useState([])
  const [tickers, setTickers] = useState([])
  const [skipped, setSkipped] = useState([])

  const parsedTickers = useMemo(() => {
    const dedup = []
    const seen = new Set()
    for (const raw of input.split(',').map((s) => s.trim().toUpperCase()).filter(Boolean)) {
      if (seen.has(raw)) continue
      seen.add(raw)
      dedup.push(raw)
      if (dedup.length >= 6) break
    }
    return dedup
  }, [input])

  const runCompare = async () => {
    if (parsedTickers.length < 2) {
      setError('Please enter at least 2 tickers')
      return
    }
    setLoading(true)
    setError('')
    try {
      const res = await compareStocks(parsedTickers.join(','), period)
      setRows(res.data.data || [])
      setTickers(res.data.tickers || [])
      setSkipped(res.data.skipped || [])
      if (res.data.error) setError(res.data.error)
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to compare tickers')
      setRows([])
      setTickers([])
      setSkipped([])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="p-6 space-y-5">
      <h1 className="text-xl font-semibold text-slate-100">Compare</h1>

      <div className="card space-y-4">
        <div className="flex flex-wrap items-center gap-3">
          <input
            className="input max-w-xl uppercase"
            placeholder="AAPL, KO, SMR"
            value={input}
            onChange={(e) => setInput(e.target.value)}
          />
          <button className="btn-primary" onClick={runCompare} disabled={loading}>
            {loading ? 'Comparing…' : 'Compare'}
          </button>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-500">Period:</span>
          {PERIODS.map((p) => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
                period === p ? 'bg-blue-600 text-white' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-700'
              }`}
            >
              {p}
            </button>
          ))}
        </div>

        {!!error && <p className="text-sm text-red-400">{error}</p>}
        {skipped.length > 0 && (
          <p className="text-xs text-amber-300">Skipped: {skipped.join(', ')}</p>
        )}
      </div>

      <div className="card">
        <p className="card-title">Normalized Price Comparison (Base = 100)</p>
        {rows.length === 0 ? (
          <p className="text-sm text-slate-500">No comparison data yet.</p>
        ) : (
          <ResponsiveContainer width="100%" height={360}>
            <LineChart data={rows} margin={{ top: 5, right: 15, left: 5, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="date" tick={{ fill: '#64748b', fontSize: 10 }} tickFormatter={(d) => d.slice(5)} />
              <YAxis tick={{ fill: '#64748b', fontSize: 10 }} />
              <Tooltip content={<ChartTooltip />} />
              <Legend />
              {tickers.map((ticker, idx) => (
                <Line
                  key={ticker}
                  type="monotone"
                  dataKey={ticker}
                  stroke={COLORS[idx % COLORS.length]}
                  strokeWidth={2}
                  dot={false}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  )
}
