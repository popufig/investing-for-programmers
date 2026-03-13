import { useEffect, useState } from 'react'
import { TrendingUp, TrendingDown, DollarSign, Layers } from 'lucide-react'
import {
  ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip,
  CartesianGrid, PieChart, Pie, Cell, Legend,
} from 'recharts'
import { getSummary, getPerformance } from '../api/client'
import { fmtCurrency, fmtPct, gainColor } from '../utils/format'

const COLORS = ['#3b82f6', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#f97316']

function StatCard({ icon: Icon, label, value, sub, subColor }) {
  return (
    <div className="card flex items-start gap-4">
      <div className="p-2.5 bg-slate-700 rounded-lg shrink-0">
        <Icon size={20} className="text-blue-400" />
      </div>
      <div className="min-w-0">
        <p className="card-title mb-1">{label}</p>
        <p className="text-2xl font-semibold text-slate-100">{value}</p>
        {sub && <p className={`text-sm mt-0.5 ${subColor || 'text-slate-400'}`}>{sub}</p>}
      </div>
    </div>
  )
}

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="card !p-3 text-xs space-y-1 min-w-[150px]">
      <p className="text-slate-400">{label}</p>
      {payload.map((p) => (
        <p key={p.name} style={{ color: p.color }}>
          {p.name}: {p.name === 'return_pct' ? fmtPct(p.value) : fmtCurrency(p.value)}
        </p>
      ))}
    </div>
  )
}

export default function Dashboard() {
  const [summary, setSummary] = useState(null)
  const [perf, setPerf] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([getSummary(), getPerformance()])
      .then(([s, p]) => {
        setSummary(s.data)
        setPerf(p.data.data || [])
      })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-slate-400 animate-pulse">Loading portfolio…</div>
      </div>
    )
  }

  const gl = summary?.total_gain_loss || 0
  const glPct = summary?.total_gain_loss_pct || 0

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-xl font-semibold text-slate-100">Portfolio Overview</h1>

      {/* Stat cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <StatCard
          icon={DollarSign}
          label="Total Value"
          value={fmtCurrency(summary?.total_value)}
          sub={`Cost: ${fmtCurrency(summary?.total_cost)}`}
        />
        <StatCard
          icon={gl >= 0 ? TrendingUp : TrendingDown}
          label="Unrealised Gain / Loss"
          value={fmtCurrency(gl)}
          sub={fmtPct(glPct)}
          subColor={gainColor(gl)}
        />
        <StatCard
          icon={Layers}
          label="Asset Types"
          value={summary?.by_type?.length ?? 0}
          sub={summary?.by_type?.map((t) => t.name).join(' · ')}
        />
        <StatCard
          icon={Layers}
          label="Portfolios"
          value={summary?.by_portfolio?.length ?? 0}
          sub={summary?.by_portfolio?.map((p) => p.name).join(' · ')}
        />
      </div>

      {/* Performance chart */}
      <div className="card">
        <p className="card-title">Portfolio Value — Past 12 Months</p>
        {perf.length > 0 ? (
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={perf} margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis
                dataKey="date"
                tick={{ fill: '#94a3b8', fontSize: 11 }}
                tickFormatter={(d) => d.slice(5)}
                interval={Math.floor(perf.length / 8)}
              />
              <YAxis
                tick={{ fill: '#94a3b8', fontSize: 11 }}
                tickFormatter={(v) => fmtCurrency(v, 0)}
                width={80}
              />
              <Tooltip content={<CustomTooltip />} />
              <Line
                type="monotone" dataKey="value" stroke="#3b82f6"
                strokeWidth={2} dot={false} name="value"
              />
              <Line
                type="monotone" dataKey="cost" stroke="#475569"
                strokeWidth={1.5} dot={false} strokeDasharray="4 2" name="cost"
              />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <p className="text-slate-500 text-sm py-8 text-center">No performance data available.</p>
        )}
      </div>

      {/* Allocation charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <AllocationChart title="By Asset Type" data={summary?.by_type || []} />
        <AllocationChart title="By Portfolio" data={summary?.by_portfolio || []} />
      </div>
    </div>
  )
}

function AllocationChart({ title, data }) {
  return (
    <div className="card">
      <p className="card-title">{title}</p>
      {data.length > 0 ? (
        <ResponsiveContainer width="100%" height={220}>
          <PieChart>
            <Pie
              data={data} cx="50%" cy="50%" outerRadius={80}
              dataKey="value" nameKey="name"
              label={({ name, pct }) => `${name} ${pct}%`}
              labelLine={false}
            >
              {data.map((_, i) => (
                <Cell key={i} fill={COLORS[i % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip
              formatter={(v) => fmtCurrency(v)}
              contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8 }}
            />
            <Legend
              formatter={(v) => <span className="text-xs text-slate-300">{v}</span>}
            />
          </PieChart>
        </ResponsiveContainer>
      ) : (
        <p className="text-slate-500 text-sm py-8 text-center">No data.</p>
      )}
    </div>
  )
}
