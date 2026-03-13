import { useEffect, useMemo, useState } from 'react'
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Cell,
  Legend,
} from 'recharts'
import { getEpsTrend } from '../api/client'
import { fmtNumber, fmtPct } from '../utils/format'

const COMPARE_COLORS = ['#3b82f6', '#22c55e', '#f59e0b', '#a78bfa', '#ef4444']
const DEFAULT_EPS_PEERS = {
  AEVA: 'LAZR, INVZ, OUST',
  LAZR: 'AEVA, INVZ, OUST',
  INVZ: 'AEVA, LAZR, OUST',
  OUST: 'AEVA, LAZR, INVZ',
}

function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div className="card !p-2 text-xs">
      <p className="text-slate-400 mb-1">{label}</p>
      <p className="text-slate-200">EPS: {fmtNumber(payload[0].value, 4)}</p>
    </div>
  )
}

export default function EpsTrend({ ticker }) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [data, setData] = useState(null)
  const [compareInput, setCompareInput] = useState('')
  const [compareLoading, setCompareLoading] = useState(false)
  const [compareError, setCompareError] = useState('')
  const [compareSeries, setCompareSeries] = useState({})

  const mainTicker = (ticker || '').toUpperCase().trim()

  useEffect(() => {
    if (!mainTicker) return
    let ignore = false

    const run = async () => {
      setLoading(true)
      setError('')
      try {
        const res = await getEpsTrend(mainTicker)
        if (!ignore) setData(res.data)
      } catch (e) {
        if (!ignore) {
          setError(e.response?.data?.detail || 'Failed to load EPS trend')
          setData(null)
        }
      } finally {
        if (!ignore) setLoading(false)
      }
    }

    run()
    return () => { ignore = true }
  }, [mainTicker])

  useEffect(() => {
    if (!mainTicker) return
    setCompareInput(DEFAULT_EPS_PEERS[mainTicker] || '')
    setCompareError('')
    setCompareSeries({})
  }, [mainTicker])

  const rows = useMemo(() => data?.eps_history || [], [data])
  const compareTickers = useMemo(
    () => Object.keys(compareSeries),
    [compareSeries]
  )
  const overlayRows = useMemo(() => {
    if (compareTickers.length < 2) return []
    const years = new Set()
    const perTicker = {}
    for (const symbol of compareTickers) {
      const history = compareSeries[symbol] || []
      const map = {}
      history.forEach((row) => {
        if (!row?.year) return
        years.add(row.year)
        map[row.year] = row.eps
      })
      perTicker[symbol] = map
    }

    const orderedYears = [...years].sort((a, b) => Number(a) - Number(b))
    return orderedYears.map((year) => {
      const item = { year }
      compareTickers.forEach((symbol) => {
        const value = perTicker[symbol]?.[year]
        item[symbol] = value == null ? null : Number(value)
      })
      return item
    })
  }, [compareSeries, compareTickers])

  const runCompare = async () => {
    if (!mainTicker) return
    const peers = []
    const seen = new Set([mainTicker])
    compareInput
      .split(',')
      .map((s) => s.trim().toUpperCase())
      .filter(Boolean)
      .forEach((symbol) => {
        if (seen.has(symbol) || peers.length >= 4) return
        seen.add(symbol)
        peers.push(symbol)
      })

    if (peers.length === 0) {
      setCompareError('Enter at least one peer ticker')
      setCompareSeries({})
      return
    }

    setCompareLoading(true)
    setCompareError('')

    try {
      const symbols = [mainTicker, ...peers]
      const settled = await Promise.allSettled(symbols.map((symbol) => getEpsTrend(symbol)))
      const nextSeries = {}
      settled.forEach((res, idx) => {
        if (res.status !== 'fulfilled') return
        const symbol = symbols[idx]
        const history = res.value?.data?.eps_history || []
        if (history.length > 0) nextSeries[symbol] = history
      })

      if (Object.keys(nextSeries).length < 2) {
        setCompareError('Not enough EPS history to compare these tickers')
        setCompareSeries({})
        return
      }

      setCompareSeries(nextSeries)
    } catch (e) {
      setCompareError(e.response?.data?.detail || 'Failed to compare EPS trends')
      setCompareSeries({})
    } finally {
      setCompareLoading(false)
    }
  }

  return (
    <div className="card">
      <div className="flex items-center justify-between gap-3 mb-3">
        <p className="card-title !mb-0">Annual EPS Trend</p>
        {rows.length > 0 && (
          <p className="text-xs text-slate-500">
            {data?.earliest_year} - {data?.latest_year}
          </p>
        )}
      </div>

      {loading && <p className="text-sm text-slate-500">Loading EPS trend…</p>}
      {!loading && error && <p className="text-sm text-red-400">{error}</p>}
      {!loading && !error && data?.error && rows.length === 0 && (
        <p className="text-sm text-slate-500">{data.error}</p>
      )}
      {!loading && !error && !data?.error && rows.length === 0 && (
        <p className="text-sm text-slate-500">Annual EPS data is not available for this ticker.</p>
      )}

      {!loading && !error && rows.length > 0 && (
        <div className="space-y-4">
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={rows} margin={{ top: 5, right: 10, left: 8, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="year" tick={{ fill: '#64748b', fontSize: 10 }} />
              <YAxis tick={{ fill: '#64748b', fontSize: 10 }} width={60} />
              <Tooltip content={<ChartTooltip />} />
              <Bar dataKey="eps" name="EPS">
                {rows.map((entry) => (
                  <Cell key={entry.year} fill={entry.eps >= 0 ? '#22c55e' : '#ef4444'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>

          <div className="overflow-x-auto">
            <table className="w-full text-xs min-w-[380px]">
              <thead>
                <tr className="border-b border-slate-700">
                  <th className="th">Year</th>
                  <th className="th text-right">EPS</th>
                  <th className="th text-right">YoY</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => {
                  const yoyPct = row.yoy_change == null ? null : row.yoy_change * 100
                  const yoyClass = yoyPct == null ? 'text-slate-400' : yoyPct >= 0 ? 'text-emerald-400' : 'text-red-400'
                  return (
                    <tr key={row.year} className="table-row">
                      <td className="td text-slate-200">{row.year}</td>
                      <td className={`td text-right ${row.eps >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                        {fmtNumber(row.eps, 4)}
                      </td>
                      <td className={`td text-right ${yoyClass}`}>{fmtPct(yoyPct, 2)}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <div className="mt-4 pt-4 border-t border-slate-700">
        <div className="flex items-center justify-between gap-2 mb-2">
          <p className="text-xs text-slate-400">Peer Overlay (concurrent single-ticker calls)</p>
          <button
            type="button"
            className="btn-primary !py-1.5"
            onClick={runCompare}
            disabled={compareLoading || !mainTicker}
          >
            {compareLoading ? 'Comparing…' : 'Compare'}
          </button>
        </div>
        <input
          className="input uppercase mb-2"
          value={compareInput}
          onChange={(e) => setCompareInput(e.target.value)}
          placeholder="Peers, comma separated (e.g. LAZR,INVZ,OUST)"
        />
        {compareError && <p className="text-xs text-red-400 mb-2">{compareError}</p>}
        {overlayRows.length > 0 && (
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={overlayRows} margin={{ top: 5, right: 10, left: 8, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="year" tick={{ fill: '#64748b', fontSize: 10 }} />
              <YAxis tick={{ fill: '#64748b', fontSize: 10 }} width={60} />
              <Tooltip content={<ChartTooltip />} />
              <Legend />
              {compareTickers.map((symbol, idx) => (
                <Line
                  key={symbol}
                  type="monotone"
                  dataKey={symbol}
                  stroke={COMPARE_COLORS[idx % COMPARE_COLORS.length]}
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
