import { useEffect, useMemo, useState } from 'react'
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  AreaChart,
  Area,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts'
import { getFinancials, getRatioTrends } from '../api/client'
import { fmtCurrency, fmtNumber } from '../utils/format'

const TABS = [
  { key: 'income', label: 'Income' },
  { key: 'balance', label: 'Balance Sheet' },
  { key: 'cash', label: 'Cash Flow' },
  { key: 'ratios', label: 'Ratios' },
]

const COLORS = {
  revenue: '#3b82f6',
  gross: '#10b981',
  net: '#a78bfa',
  rnd: '#f59e0b',
  assets: '#3b82f6',
  liabilities: '#ef4444',
  equity: '#22c55e',
  ocf: '#22c55e',
  fcf: '#3b82f6',
  debt_to_equity: '#ef4444',
  current_ratio: '#22c55e',
  roe: '#3b82f6',
  profit_margin: '#f59e0b',
  roa: '#a78bfa',
  asset_turnover: '#14b8a6',
}

const RATIO_META = [
  { key: 'debt_to_equity', label: 'Debt/Equity' },
  { key: 'current_ratio', label: 'Current Ratio' },
  { key: 'roe', label: 'ROE' },
  { key: 'profit_margin', label: 'Profit Margin' },
  { key: 'roa', label: 'ROA' },
  { key: 'asset_turnover', label: 'Asset Turnover' },
]

function ChartTooltip({ active, payload, label, formatter }) {
  if (!active || !payload?.length) return null
  return (
    <div className="card !p-2 text-xs">
      <p className="text-slate-400 mb-1">{label}</p>
      {payload.map((item) => (
        <p key={item.dataKey} style={{ color: item.color }}>
          {item.name}: {formatter ? formatter(item.value) : item.value}
        </p>
      ))}
    </div>
  )
}

export default function FinancialStatements({ ticker }) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [activeTab, setActiveTab] = useState('income')
  const [data, setData] = useState({ income_statement: [], balance_sheet: [], cash_flow: [] })
  const [ratioData, setRatioData] = useState({ periods: [], ratios: {} })
  const [visibleRatios, setVisibleRatios] = useState({
    debt_to_equity: true,
    current_ratio: true,
    roe: false,
    profit_margin: false,
    roa: false,
    asset_turnover: false,
  })

  useEffect(() => {
    if (!ticker) return
    let ignore = false

    const run = async () => {
      setLoading(true)
      setError('')
      try {
        const [financialRes, ratioRes] = await Promise.all([
          getFinancials(ticker),
          getRatioTrends(ticker),
        ])
        if (ignore) return
        setData({
          income_statement: financialRes.data.income_statement || [],
          balance_sheet: financialRes.data.balance_sheet || [],
          cash_flow: financialRes.data.cash_flow || [],
        })
        setRatioData({
          periods: ratioRes.data.periods || [],
          ratios: ratioRes.data.ratios || {},
        })
      } catch (e) {
        if (!ignore) {
          setError(e.response?.data?.detail || 'Failed to load financial statements')
          setData({ income_statement: [], balance_sheet: [], cash_flow: [] })
          setRatioData({ periods: [], ratios: {} })
        }
      } finally {
        if (!ignore) setLoading(false)
      }
    }

    run()
    return () => { ignore = true }
  }, [ticker])

  const incomeData = useMemo(
    () => data.income_statement.map((row) => ({
      period: row.period,
      revenue: row.total_revenue,
      gross: row.gross_profit,
      net: row.net_income,
      rnd: row.research_and_development,
    })),
    [data.income_statement],
  )

  const balanceData = useMemo(
    () => data.balance_sheet.map((row) => ({
      period: row.period,
      assets: row.total_assets,
      liabilities: row.total_liabilities,
      equity: row.stockholders_equity,
    })),
    [data.balance_sheet],
  )

  const cashData = useMemo(
    () => data.cash_flow.map((row) => ({
      period: row.period,
      ocf: row.operating_cash_flow,
      fcf: row.free_cash_flow,
      capex: row.capital_expenditure,
    })),
    [data.cash_flow],
  )

  const ratiosChartData = useMemo(() => {
    if (!ratioData?.periods?.length) return []
    return ratioData.periods.map((period, idx) => ({
      period,
      debt_to_equity: ratioData.ratios?.debt_to_equity?.[idx] ?? null,
      current_ratio: ratioData.ratios?.current_ratio?.[idx] ?? null,
      roe: ratioData.ratios?.roe?.[idx] ?? null,
      profit_margin: ratioData.ratios?.profit_margin?.[idx] ?? null,
      roa: ratioData.ratios?.roa?.[idx] ?? null,
      asset_turnover: ratioData.ratios?.asset_turnover?.[idx] ?? null,
    }))
  }, [ratioData])

  const hasAnyData = incomeData.length || balanceData.length || cashData.length || ratiosChartData.length

  const toggleRatio = (key) => {
    setVisibleRatios((prev) => ({ ...prev, [key]: !prev[key] }))
  }

  return (
    <div className="card">
      <div className="flex items-center justify-between gap-3 mb-3">
        <p className="card-title !mb-0">Financial Statements</p>
        <div className="flex gap-2">
          {TABS.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`px-2.5 py-1 rounded text-xs ${
                activeTab === tab.key
                  ? 'bg-blue-600 text-white'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-700'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {loading && <p className="text-sm text-slate-500">Loading financial statements…</p>}
      {!loading && error && <p className="text-sm text-red-400">{error}</p>}
      {!loading && !error && !hasAnyData && (
        <p className="text-sm text-slate-500">Financial statement data is not available for this ticker.</p>
      )}

      {!loading && !error && hasAnyData && activeTab === 'income' && (
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={incomeData} margin={{ top: 5, right: 12, left: 8, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
            <XAxis dataKey="period" tick={{ fill: '#64748b', fontSize: 10 }} />
            <YAxis tick={{ fill: '#64748b', fontSize: 10 }} tickFormatter={(v) => fmtCurrency(v)} width={74} />
            <Tooltip content={<ChartTooltip formatter={(v) => fmtCurrency(v)} />} />
            <Bar dataKey="revenue" fill={COLORS.revenue} name="Revenue" />
            <Bar dataKey="gross" fill={COLORS.gross} name="Gross Profit" />
            <Bar dataKey="net" fill={COLORS.net} name="Net Income" />
            <Bar dataKey="rnd" fill={COLORS.rnd} name="R&D" />
          </BarChart>
        </ResponsiveContainer>
      )}

      {!loading && !error && hasAnyData && activeTab === 'balance' && (
        <ResponsiveContainer width="100%" height={280}>
          <AreaChart data={balanceData} margin={{ top: 5, right: 12, left: 8, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
            <XAxis dataKey="period" tick={{ fill: '#64748b', fontSize: 10 }} />
            <YAxis tick={{ fill: '#64748b', fontSize: 10 }} tickFormatter={(v) => fmtCurrency(v)} width={74} />
            <Tooltip content={<ChartTooltip formatter={(v) => fmtCurrency(v)} />} />
            <Area type="monotone" dataKey="assets" stackId="1" stroke={COLORS.assets} fill={COLORS.assets} fillOpacity={0.35} name="Total Assets" />
            <Area type="monotone" dataKey="liabilities" stackId="2" stroke={COLORS.liabilities} fill={COLORS.liabilities} fillOpacity={0.25} name="Total Liabilities" />
            <Area type="monotone" dataKey="equity" stackId="3" stroke={COLORS.equity} fill={COLORS.equity} fillOpacity={0.25} name="Equity" />
          </AreaChart>
        </ResponsiveContainer>
      )}

      {!loading && !error && hasAnyData && activeTab === 'cash' && (
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={cashData} margin={{ top: 5, right: 12, left: 8, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
            <XAxis dataKey="period" tick={{ fill: '#64748b', fontSize: 10 }} />
            <YAxis tick={{ fill: '#64748b', fontSize: 10 }} tickFormatter={(v) => fmtCurrency(v)} width={74} />
            <Tooltip content={<ChartTooltip formatter={(v) => fmtCurrency(v)} />} />
            <Bar dataKey="ocf" fill={COLORS.ocf} name="Operating Cash Flow" />
            <Bar dataKey="fcf" fill={COLORS.fcf} name="Free Cash Flow" />
          </BarChart>
        </ResponsiveContainer>
      )}

      {!loading && !error && hasAnyData && activeTab === 'ratios' && (
        <>
          <div className="flex flex-wrap gap-2 mb-3">
            {RATIO_META.map((ratio) => (
              <button
                key={ratio.key}
                onClick={() => toggleRatio(ratio.key)}
                className={`px-2.5 py-1 rounded text-xs ${
                  visibleRatios[ratio.key]
                    ? 'bg-slate-700 text-slate-100'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-700/60'
                }`}
              >
                {ratio.label}
              </button>
            ))}
          </div>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={ratiosChartData} margin={{ top: 5, right: 12, left: 8, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="period" tick={{ fill: '#64748b', fontSize: 10 }} />
              <YAxis tick={{ fill: '#64748b', fontSize: 10 }} width={60} />
              <Tooltip content={<ChartTooltip formatter={(v) => fmtNumber(v, 4)} />} />
              <Legend />
              {RATIO_META.map((ratio) => (
                visibleRatios[ratio.key] && (
                  <Line
                    key={ratio.key}
                    type="monotone"
                    dataKey={ratio.key}
                    stroke={COLORS[ratio.key]}
                    strokeWidth={ratio.key === 'debt_to_equity' ? 2.5 : 1.8}
                    dot={false}
                    name={ratio.label}
                  />
                )
              ))}
            </LineChart>
          </ResponsiveContainer>
        </>
      )}
    </div>
  )
}
