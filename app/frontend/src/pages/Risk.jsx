import { useEffect, useState } from 'react'
import { RefreshCw, Info } from 'lucide-react'
import {
  ResponsiveContainer, RadarChart, Radar, PolarGrid, PolarAngleAxis,
  Tooltip, ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, ZAxis,
} from 'recharts'
import { getPortfolioRisk } from '../api/client'
import { fmtPct } from '../utils/format'

function RiskCard({ label, value, description, color }) {
  return (
    <div className="card">
      <div className="flex items-start justify-between mb-2">
        <p className="text-xs text-slate-400 uppercase tracking-wide">{label}</p>
        <span title={description} className="text-slate-600 cursor-help"><Info size={12} /></span>
      </div>
      <p className={`text-2xl font-bold ${color || 'text-slate-100'}`}>{value}</p>
      <p className="text-xs text-slate-500 mt-1 leading-snug">{description}</p>
    </div>
  )
}

export default function Risk() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = () => {
    setLoading(true)
    getPortfolioRisk()
      .then((r) => setData(r.data))
      .catch((e) => setError(e.response?.data?.error || 'Failed to load risk data'))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <p className="text-slate-400 animate-pulse">Computing risk metrics…</p>
    </div>
  )

  if (error) return (
    <div className="p-6">
      <div className="card text-center py-12">
        <p className="text-red-400 mb-2">{error}</p>
        <button onClick={load} className="btn-primary mt-3"><RefreshCw size={14} /> Retry</button>
      </div>
    </div>
  )

  const { portfolio: p, stocks, correlation, tickers } = data || {}
  const stockList = Object.entries(stocks || {}).map(([t, m]) => ({ ticker: t, ...m }))

  // Radar chart: per-stock sharpe/return/risk
  const radarData = stockList.map((s) => ({
    subject: s.ticker,
    'Return %': Math.max(0, Math.min(100, s.annual_return + 50)),
    'Sharpe':   Math.max(0, Math.min(100, (s.sharpe + 2) * 25)),
    'Low Risk': Math.max(0, 100 - s.annual_vol),
  }))

  // Scatter: risk vs return
  const scatterData = stockList.map((s) => ({
    x: s.annual_vol,
    y: s.annual_return,
    z: s.weight,
    name: s.ticker,
  }))

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-slate-100">Risk Management</h1>
        <button onClick={load} className="btn-ghost"><RefreshCw size={15} /> Refresh</button>
      </div>

      {/* Portfolio-level metrics */}
      {p && (
        <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-3">
          <RiskCard
            label="VaR 95% (daily)"
            value={fmtPct(p.var_95_daily)}
            description="Max expected daily loss 95% of the time."
            color="text-amber-400"
          />
          <RiskCard
            label="VaR 99% (daily)"
            value={fmtPct(p.var_99_daily)}
            description="Max expected daily loss 99% of the time."
            color="text-red-400"
          />
          <RiskCard
            label="Sharpe Ratio"
            value={p.sharpe?.toFixed(2)}
            description="Risk-adjusted return (risk-free = 5%). >1 is good."
            color={p.sharpe >= 1 ? 'text-emerald-400' : p.sharpe >= 0 ? 'text-amber-400' : 'text-red-400'}
          />
          <RiskCard
            label="Max Drawdown"
            value={fmtPct(p.max_drawdown)}
            description="Largest peak-to-trough decline in past year."
            color="text-red-400"
          />
          <RiskCard
            label="Annual Return"
            value={fmtPct(p.annual_return)}
            description="Annualized portfolio return (past 1y)."
            color={p.annual_return >= 0 ? 'text-emerald-400' : 'text-red-400'}
          />
          <RiskCard
            label="Annual Volatility"
            value={fmtPct(p.annual_volatility)}
            description="Annualized standard deviation of portfolio returns."
            color="text-slate-100"
          />
        </div>
      )}

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Risk vs Return scatter */}
        <div className="card">
          <p className="card-title">Risk vs. Return</p>
          <ResponsiveContainer width="100%" height={240}>
            <ScatterChart margin={{ top: 10, right: 20, left: 10, bottom: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis
                type="number" dataKey="x" name="Volatility %"
                tick={{ fill: '#64748b', fontSize: 10 }} label={{ value: 'Volatility %', position: 'insideBottom', offset: -5, fill: '#64748b', fontSize: 11 }}
              />
              <YAxis
                type="number" dataKey="y" name="Return %"
                tick={{ fill: '#64748b', fontSize: 10 }} label={{ value: 'Return %', angle: -90, position: 'insideLeft', fill: '#64748b', fontSize: 11 }}
              />
              <ZAxis type="number" dataKey="z" range={[40, 300]} name="Weight %" />
              <Tooltip
                cursor={{ strokeDasharray: '3 3' }}
                content={({ active, payload }) => {
                  if (!active || !payload?.length) return null
                  const d = payload[0]?.payload
                  return (
                    <div className="card !p-2 text-xs">
                      <p className="font-bold text-blue-400">{d?.name}</p>
                      <p>Return: {fmtPct(d?.y)}</p>
                      <p>Volatility: {fmtPct(d?.x)}</p>
                      <p>Weight: {fmtPct(d?.z)}</p>
                    </div>
                  )
                }}
              />
              <Scatter data={scatterData} fill="#3b82f6" opacity={0.8} />
            </ScatterChart>
          </ResponsiveContainer>
        </div>

        {/* Radar chart */}
        {radarData.length > 2 && (
          <div className="card">
            <p className="card-title">Stock Scorecard (normalised)</p>
            <ResponsiveContainer width="100%" height={240}>
              <RadarChart data={radarData}>
                <PolarGrid stroke="#334155" />
                <PolarAngleAxis dataKey="subject" tick={{ fill: '#94a3b8', fontSize: 11 }} />
                <Radar name="Return" dataKey="Return %" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.2} />
                <Radar name="Sharpe" dataKey="Sharpe" stroke="#22c55e" fill="#22c55e" fillOpacity={0.2} />
                <Radar name="Low Risk" dataKey="Low Risk" stroke="#f59e0b" fill="#f59e0b" fillOpacity={0.2} />
                <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8, fontSize: 11 }} />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {/* Correlation matrix */}
      {tickers && tickers.length > 1 && (
        <div className="card">
          <p className="card-title">Correlation Matrix</p>
          <p className="text-xs text-slate-500 mb-4">
            1.0 = perfect positive correlation (move together), -1.0 = inverse. Aim for low correlations to diversify.
          </p>
          <div className="overflow-x-auto">
            <table className="text-xs">
              <thead>
                <tr>
                  <th className="th w-16" />
                  {tickers.map((t) => <th key={t} className="th text-center">{t}</th>)}
                </tr>
              </thead>
              <tbody>
                {tickers.map((row) => (
                  <tr key={row} className="border-b border-slate-800">
                    <td className="td font-mono text-blue-400">{row}</td>
                    {tickers.map((col) => {
                      const v = correlation?.[col]?.[row] ?? 0
                      const abs = Math.abs(v)
                      const bg = v === 1
                        ? '#1d4ed8'
                        : v > 0
                        ? `rgba(59,130,246,${abs * 0.6})`
                        : `rgba(239,68,68,${abs * 0.6})`
                      return (
                        <td key={col} className="td text-center" style={{ background: bg, minWidth: 52 }}>
                          <span className={v >= 0.7 || v <= -0.7 ? 'text-white font-semibold' : 'text-slate-300'}>
                            {v.toFixed(2)}
                          </span>
                        </td>
                      )
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Per-stock risk table */}
      {stockList.length > 0 && (
        <div className="card">
          <p className="card-title">Individual Stock Risk Metrics</p>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-700">
                  {['Ticker', 'Weight %', 'Annual Return', 'Volatility', 'Sharpe', 'Max Drawdown', 'VaR 95% daily'].map((h) => (
                    <th key={h} className="th">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {stockList.sort((a, b) => b.weight - a.weight).map((s) => (
                  <tr key={s.ticker} className="table-row">
                    <td className="td font-mono font-semibold text-blue-400">{s.ticker}</td>
                    <td className="td text-right">{fmtPct(s.weight, 1)}</td>
                    <td className={`td text-right font-medium ${s.annual_return >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                      {fmtPct(s.annual_return)}
                    </td>
                    <td className="td text-right">{fmtPct(s.annual_vol)}</td>
                    <td className={`td text-right ${s.sharpe >= 1 ? 'text-emerald-400' : s.sharpe >= 0 ? 'text-amber-400' : 'text-red-400'}`}>
                      {s.sharpe?.toFixed(2)}
                    </td>
                    <td className="td text-right text-red-400">{fmtPct(s.max_drawdown)}</td>
                    <td className="td text-right text-amber-400">{fmtPct(s.var_95)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
