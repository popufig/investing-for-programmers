import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Search } from 'lucide-react'
import {
  ResponsiveContainer,
  ComposedChart,
  LineChart,
  BarChart,
  Line,
  Bar,
  Cell,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ReferenceLine,
  RadialBarChart,
  RadialBar,
  PolarAngleAxis,
  Legend,
} from 'recharts'
import {
  compareStocks,
  getEsgData,
  getHistory,
  getReturns,
  getSentiment,
  getStock,
  getTechnicals,
} from '../api/client'
import { fmtCurrency, fmtNumber, fmtPct, marketCapLabel } from '../utils/format'
import AnalystSection from '../components/AnalystSection'
import AthAnalysis from '../components/AthAnalysis'
import EconomicCycleSection from '../components/EconomicCycleSection'
import EarningsEstimates from '../components/EarningsEstimates'
import EpsTrend from '../components/EpsTrend'
import FinancialStatements from '../components/FinancialStatements'
import FredRateChart from '../components/FredRateChart'
import GoogleTrends from '../components/GoogleTrends'
import PeerComparison from '../components/PeerComparison'

const PERIODS = ['3mo', '6mo', '1y', '2y', '5y']
const COMPARE_COLORS = ['#3b82f6', '#22c55e', '#f59e0b', '#a78bfa', '#ef4444', '#14b8a6']
const SENTIMENT_COLORS = {
  Bullish: '#22c55e',
  'Somewhat-Bullish': '#86efac',
  Neutral: '#94a3b8',
  'Somewhat-Bearish': '#f59e0b',
  Bearish: '#ef4444',
}
const SENTIMENT_ORDER = ['Bullish', 'Somewhat-Bullish', 'Neutral', 'Somewhat-Bearish', 'Bearish']

function MetricCard({ label, value, sub, color }) {
  return (
    <div className="bg-slate-900 border border-slate-700 rounded-lg p-3">
      <p className="text-xs text-slate-500 mb-1">{label}</p>
      <p className={`text-base font-semibold ${color || 'text-slate-100'}`}>{value ?? '—'}</p>
      {sub && <p className="text-xs text-slate-500 mt-0.5">{sub}</p>}
    </div>
  )
}

function Section({ title, children }) {
  return (
    <div className="card">
      <p className="card-title">{title}</p>
      {children}
    </div>
  )
}

function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div className="card !p-2.5 text-xs space-y-0.5 min-w-[160px] z-10">
      <p className="text-slate-400 mb-1">{label}</p>
      {payload.map((p) => (
        <p key={`${p.name}-${p.dataKey}`} style={{ color: p.color }}>
          {p.name}: {typeof p.value === 'number' ? p.value.toFixed(4) : p.value}
        </p>
      ))}
    </div>
  )
}

function EsgWidget({ loading, data }) {
  if (loading) return <p className="text-xs text-slate-500">Loading ESG…</p>
  if (!data?.available) return <p className="text-xs text-slate-500">ESG data not available.</p>

  const score = Math.min(100, Math.max(0, data.total_score ?? 0))
  const color = score <= 30 ? '#22c55e' : score <= 60 ? '#f59e0b' : '#ef4444'

  return (
    <div className="mt-3 border border-slate-700 rounded-lg p-3 bg-slate-900/70">
      <div className="flex items-center justify-between mb-2">
        <p className="text-xs text-slate-400">ESG Score</p>
        <p className="text-sm font-semibold" style={{ color }}>{fmtNumber(data.total_score, 1)}</p>
      </div>

      <div className="h-[120px]">
        <ResponsiveContainer width="100%" height="100%">
          <RadialBarChart innerRadius="70%" outerRadius="100%" data={[{ value: score, fill: color }]} startAngle={90} endAngle={-270}>
            <PolarAngleAxis type="number" domain={[0, 100]} tick={false} />
            <RadialBar dataKey="value" cornerRadius={10} background />
          </RadialBarChart>
        </ResponsiveContainer>
      </div>

      <div className="flex flex-wrap gap-2 mt-1">
        <span className="badge bg-slate-800 text-slate-300">E {fmtNumber(data.environment_score, 1)}</span>
        <span className="badge bg-slate-800 text-slate-300">S {fmtNumber(data.social_score, 1)}</span>
        <span className="badge bg-slate-800 text-slate-300">G {fmtNumber(data.governance_score, 1)}</span>
      </div>
    </div>
  )
}

export default function StockAnalysis() {
  const { ticker: urlTicker } = useParams()
  const navigate = useNavigate()

  const [query, setQuery] = useState(urlTicker || '')
  const [info, setInfo] = useState(null)
  const [techData, setTechData] = useState([])
  const [priceData, setPriceData] = useState([])
  const [period, setPeriod] = useState('1y')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [activeIndicators, setActiveIndicators] = useState({
    sma20: true, sma50: true, sma200: false, bb: false,
  })

  const [esgData, setEsgData] = useState(null)
  const [esgLoading, setEsgLoading] = useState(false)

  const [compareInput, setCompareInput] = useState('')
  const [compareRows, setCompareRows] = useState([])
  const [compareTickers, setCompareTickers] = useState([])
  const [compareSkipped, setCompareSkipped] = useState([])
  const [compareLoading, setCompareLoading] = useState(false)
  const [compareError, setCompareError] = useState('')

  const [returnsData, setReturnsData] = useState(null)
  const [returnsLoading, setReturnsLoading] = useState(false)

  const [sentimentData, setSentimentData] = useState(null)
  const [sentimentLoading, setSentimentLoading] = useState(false)

  const loadStock = async (ticker) => {
    const t = ticker.toUpperCase().trim()
    if (!t) return

    setLoading(true)
    setError('')
    setEsgData(null)
    setCompareRows([])
    setCompareTickers([])
    setCompareSkipped([])
    setCompareError('')

    try {
      const [infoRes, techRes, priceRes] = await Promise.all([
        getStock(t),
        getTechnicals(t, period),
        getHistory(t, period),
      ])
      setInfo(infoRes.data)
      setTechData(techRes.data.data || [])
      setPriceData(priceRes.data.data || [])
    } catch (e) {
      setError(e.response?.data?.detail || 'Ticker not found')
      setInfo(null)
      setTechData([])
      setPriceData([])
      setEsgData(null)
      setReturnsData(null)
      setSentimentData(null)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (urlTicker) loadStock(urlTicker)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [urlTicker, period])

  useEffect(() => {
    if (urlTicker) setQuery(urlTicker)
  }, [urlTicker])

  useEffect(() => {
    if (!info?.ticker) return
    let ignore = false

    const loadEsg = async () => {
      setEsgLoading(true)
      try {
        const res = await getEsgData(info.ticker)
        if (!ignore) setEsgData(res.data)
      } catch {
        if (!ignore) {
          setEsgData({
            ticker: info.ticker,
            available: false,
            total_score: null,
            environment_score: null,
            social_score: null,
            governance_score: null,
            performance: null,
          })
        }
      } finally {
        if (!ignore) setEsgLoading(false)
      }
    }

    loadEsg()
    return () => { ignore = true }
  }, [info?.ticker])

  useEffect(() => {
    if (!info?.ticker) return
    let ignore = false

    const loadReturns = async () => {
      setReturnsLoading(true)
      try {
        const res = await getReturns(info.ticker, period)
        if (!ignore) setReturnsData(res.data)
      } catch (e) {
        if (!ignore) setReturnsData({ error: e.response?.data?.detail || 'Failed to load returns' })
      } finally {
        if (!ignore) setReturnsLoading(false)
      }
    }

    loadReturns()
    return () => { ignore = true }
  }, [info?.ticker, period])

  useEffect(() => {
    if (!info?.ticker) return
    let ignore = false

    const loadSentiment = async () => {
      setSentimentLoading(true)
      try {
        const res = await getSentiment(info.ticker)
        if (!ignore) setSentimentData(res.data)
      } catch (e) {
        if (!ignore) setSentimentData({
          ticker: info.ticker,
          available: false,
          message: e.response?.data?.detail || 'Failed to load sentiment',
        })
      } finally {
        if (!ignore) setSentimentLoading(false)
      }
    }

    loadSentiment()
    return () => { ignore = true }
  }, [info?.ticker])

  const handleSearch = (e) => {
    e.preventDefault()
    const t = query.toUpperCase().trim()
    if (!t) return
    if (urlTicker?.toUpperCase() === t) {
      loadStock(t)
      return
    }
    navigate(`/stocks/${t}`)
  }

  const runCompare = async () => {
    if (!info?.ticker) return
    const peers = []
    const seen = new Set([info.ticker.toUpperCase()])
    for (const raw of compareInput.split(',').map((s) => s.trim().toUpperCase()).filter(Boolean)) {
      if (seen.has(raw)) continue
      seen.add(raw)
      peers.push(raw)
      if (peers.length >= 5) break
    }
    if (peers.length < 1) {
      setCompareError('Please enter at least 1 comparison ticker')
      return
    }

    setCompareLoading(true)
    setCompareError('')
    try {
      const allTickers = [info.ticker.toUpperCase(), ...peers]
      const res = await compareStocks(allTickers.join(','), period)
      setCompareRows(res.data.data || [])
      setCompareTickers(res.data.tickers || [])
      setCompareSkipped(res.data.skipped || [])
      if (res.data.error) setCompareError(res.data.error)
    } catch (e) {
      setCompareError(e.response?.data?.detail || 'Failed to compare tickers')
      setCompareRows([])
      setCompareTickers([])
      setCompareSkipped([])
    } finally {
      setCompareLoading(false)
    }
  }

  const pct52 = info?.week_52_high && info?.week_52_low && info?.current_price
    ? ((info.current_price - info.week_52_low) / (info.week_52_high - info.week_52_low)) * 100
    : null

  const capTag = marketCapLabel(info?.market_cap_usd ?? info?.market_cap)
  const histogramRows = returnsData?.histogram?.map((x, idx) => ({
    ...x,
    bin: `${idx + 1}`,
  })) || []
  const sentimentDistRows = SENTIMENT_ORDER.map((label) => ({
    label,
    count: sentimentData?.distribution?.[label] ?? 0,
    fill: SENTIMENT_COLORS[label],
  }))

  return (
    <div className="p-6 space-y-5">
      <form onSubmit={handleSearch} className="flex gap-3 max-w-lg">
        <div className="relative flex-1">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
          <input
            className="input pl-9 uppercase"
            placeholder="Enter ticker symbol…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>
        <button type="submit" className="btn-primary" disabled={loading}>
          {loading ? 'Loading…' : 'Analyse'}
        </button>
      </form>

      {error && <p className="text-red-400 text-sm">{error}</p>}

      {!info && !loading && (
        <div className="card text-center py-16">
          <p className="text-slate-500 text-2xl mb-2">🔍</p>
          <p className="text-slate-400">Enter a ticker to start analysis.</p>
          <p className="text-slate-600 text-sm mt-1">e.g. AAPL, MSFT, SPY, BRK-B</p>
        </div>
      )}

      {info && (
        <>
          <div className="card">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <h1 className="text-2xl font-bold text-slate-100">{info.ticker}</h1>
                <p className="text-slate-400">{info.name}</p>
                {info.sector && (
                  <div className="flex items-center flex-wrap gap-2 mt-1">
                    <p className="text-xs text-slate-500">{info.sector} · {info.industry}</p>
                    {capTag && <span className={`badge text-[10px] ${capTag.color}`}>{capTag.label}</span>}
                  </div>
                )}
              </div>
              <div className="text-right">
                <p className="text-3xl font-bold text-slate-100">{fmtCurrency(info.current_price)}</p>
                {info.target_price && (
                  <p className="text-sm text-slate-400 mt-1">
                    Target: {fmtCurrency(info.target_price)}
                    <span className={`ml-2 ${info.target_price > info.current_price ? 'text-emerald-400' : 'text-red-400'}`}>
                      ({fmtPct((info.target_price - info.current_price) / info.current_price * 100)})
                    </span>
                  </p>
                )}
                {info.recommendation && (
                  <span className="badge bg-blue-900/50 text-blue-300 mt-1 capitalize">
                    {info.recommendation.replace(/_/g, ' ')}
                  </span>
                )}
              </div>
            </div>

            {pct52 != null && (
              <div className="mt-4">
                <div className="flex justify-between text-xs text-slate-500 mb-1">
                  <span>52w Low: {fmtCurrency(info.week_52_low)}</span>
                  <span>52w High: {fmtCurrency(info.week_52_high)}</span>
                </div>
                <div className="h-1.5 bg-slate-700 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-blue-500 rounded-full"
                    style={{ width: `${Math.min(100, Math.max(0, pct52))}%` }}
                  />
                </div>
              </div>
            )}

            {info.description && (
              <p className="text-xs text-slate-500 mt-4 line-clamp-3">{info.description}</p>
            )}
          </div>

          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3">
            <Section title="Valuation">
              <div className="space-y-2">
                <MetricCard label="P/E (TTM)" value={fmtNumber(info.pe_ratio, 1)} />
                <MetricCard label="P/E (Fwd)" value={fmtNumber(info.forward_pe, 1)} />
                <MetricCard label="P/B" value={fmtNumber(info.pb_ratio, 2)} />
                <MetricCard label="P/S" value={fmtNumber(info.ps_ratio, 2)} />
                <MetricCard label="EV/EBITDA" value={fmtNumber(info.ev_ebitda, 1)} />
              </div>
            </Section>
            <Section title="Profitability">
              <div className="space-y-2">
                <MetricCard label="ROE" value={info.roe != null ? fmtPct(info.roe * 100) : '—'} />
                <MetricCard label="ROA" value={info.roa != null ? fmtPct(info.roa * 100) : '—'} />
                <MetricCard label="Gross Margin" value={info.gross_margin != null ? fmtPct(info.gross_margin * 100) : '—'} />
                <MetricCard label="Net Margin" value={info.net_margin != null ? fmtPct(info.net_margin * 100) : '—'} />
                <MetricCard label="Op. Margin" value={info.operating_margin != null ? fmtPct(info.operating_margin * 100) : '—'} />
              </div>
            </Section>
            <Section title="Growth">
              <div className="space-y-2">
                <MetricCard label="EPS (TTM)" value={fmtCurrency(info.eps)} />
                <MetricCard label="EPS (Fwd)" value={fmtCurrency(info.eps_forward)} />
                <MetricCard label="Revenue Growth" value={info.revenue_growth != null ? fmtPct(info.revenue_growth * 100) : '—'} />
                <MetricCard label="Earnings Growth" value={info.earnings_growth != null ? fmtPct(info.earnings_growth * 100) : '—'} />
              </div>
            </Section>
            <Section title="Debt & Liquidity">
              <div className="space-y-2">
                <MetricCard label="D/E Ratio" value={fmtNumber(info.debt_equity, 2)} />
                <MetricCard label="Current Ratio" value={fmtNumber(info.current_ratio, 2)} />
                <MetricCard label="Quick Ratio" value={fmtNumber(info.quick_ratio, 2)} />
              </div>
            </Section>
            <Section title="Dividends & Risk">
              <div className="space-y-2">
                <MetricCard label="Div. Yield" value={info.dividend_yield != null ? fmtPct(info.dividend_yield * 100) : '—'} />
                <MetricCard label="Div. Rate" value={fmtCurrency(info.dividend_rate)} />
                <MetricCard label="Payout Ratio" value={info.payout_ratio != null ? fmtPct(info.payout_ratio * 100) : '—'} />
                <MetricCard label="Beta" value={fmtNumber(info.beta, 2)} />
                <MetricCard label="Inst. Ownership" value={info.institutional_ownership != null ? fmtPct(info.institutional_ownership * 100) : '—'} />
                <MetricCard label="Insider Ownership" value={info.insider_ownership != null ? fmtPct(info.insider_ownership * 100) : '—'} />
              </div>
              <EsgWidget loading={esgLoading} data={esgData} />
            </Section>
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

          <div className="card">
            <div className="flex flex-wrap items-center justify-between mb-3 gap-3">
              <p className="card-title !mb-0">Price Chart</p>
              <div className="flex gap-3 text-xs flex-wrap">
                {[
                  { key: 'sma20', label: 'SMA 20', color: '#f59e0b' },
                  { key: 'sma50', label: 'SMA 50', color: '#22c55e' },
                  { key: 'sma200', label: 'SMA 200', color: '#ef4444' },
                  { key: 'bb', label: 'Bollinger', color: '#8b5cf6' },
                ].map(({ key, label, color }) => (
                  <button
                    key={key}
                    onClick={() => setActiveIndicators((a) => ({ ...a, [key]: !a[key] }))}
                    className={`flex items-center gap-1.5 px-2 py-1 rounded transition-colors ${
                      activeIndicators[key] ? 'bg-slate-700' : 'opacity-40'
                    }`}
                  >
                    <span className="w-3 h-0.5 rounded-full" style={{ background: color }} />
                    <span className="text-slate-300">{label}</span>
                  </button>
                ))}
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-2 mb-3">
              <input
                className="input max-w-sm uppercase"
                placeholder="Compare tickers (e.g. KO, SMR)"
                value={compareInput}
                onChange={(e) => setCompareInput(e.target.value)}
              />
              <button className="btn-primary" onClick={runCompare} disabled={compareLoading}>
                {compareLoading ? 'Comparing…' : 'Compare'}
              </button>
              {compareError && <span className="text-xs text-red-400">{compareError}</span>}
              {compareSkipped.length > 0 && <span className="text-xs text-amber-300">Skipped: {compareSkipped.join(', ')}</span>}
            </div>

            <ResponsiveContainer width="100%" height={280}>
              <ComposedChart data={techData} margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="date" tick={{ fill: '#64748b', fontSize: 10 }} tickFormatter={(d) => d.slice(5)} interval={Math.floor(techData.length / 8)} />
                <YAxis tick={{ fill: '#64748b', fontSize: 10 }} tickFormatter={(v) => `$${v}`} width={65} domain={['auto', 'auto']} />
                <Tooltip content={<ChartTooltip />} />
                <Line type="monotone" dataKey="close" stroke="#3b82f6" strokeWidth={1.5} dot={false} name="close" />
                {activeIndicators.sma20 && <Line type="monotone" dataKey="sma20" stroke="#f59e0b" strokeWidth={1} dot={false} name="sma20" />}
                {activeIndicators.sma50 && <Line type="monotone" dataKey="sma50" stroke="#22c55e" strokeWidth={1} dot={false} name="sma50" />}
                {activeIndicators.sma200 && <Line type="monotone" dataKey="sma200" stroke="#ef4444" strokeWidth={1} dot={false} name="sma200" />}
                {activeIndicators.bb && <Line type="monotone" dataKey="bb_upper" stroke="#8b5cf6" strokeWidth={1} dot={false} strokeDasharray="3 2" name="bb_upper" />}
                {activeIndicators.bb && <Line type="monotone" dataKey="bb_lower" stroke="#8b5cf6" strokeWidth={1} dot={false} strokeDasharray="3 2" name="bb_lower" />}
              </ComposedChart>
            </ResponsiveContainer>
          </div>

          {compareRows.length > 0 && (
            <div className="card">
              <p className="card-title">Normalized Comparison (Base = 100)</p>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={compareRows} margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis dataKey="date" tick={{ fill: '#64748b', fontSize: 10 }} tickFormatter={(d) => d.slice(5)} />
                  <YAxis tick={{ fill: '#64748b', fontSize: 10 }} />
                  <Tooltip content={<ChartTooltip />} />
                  <Legend />
                  {compareTickers.map((ticker, idx) => (
                    <Line
                      key={ticker}
                      type="monotone"
                      dataKey={ticker}
                      stroke={COMPARE_COLORS[idx % COMPARE_COLORS.length]}
                      dot={false}
                      strokeWidth={2}
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div className="card">
              <p className="card-title">RSI (14)</p>
              <ResponsiveContainer width="100%" height={130}>
                <ComposedChart data={techData} margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis dataKey="date" tick={false} />
                  <YAxis domain={[0, 100]} tick={{ fill: '#64748b', fontSize: 10 }} width={30} />
                  <Tooltip content={<ChartTooltip />} />
                  <ReferenceLine y={70} stroke="#ef4444" strokeDasharray="3 2" />
                  <ReferenceLine y={30} stroke="#22c55e" strokeDasharray="3 2" />
                  <Line type="monotone" dataKey="rsi" stroke="#a78bfa" strokeWidth={1.5} dot={false} name="rsi" />
                </ComposedChart>
              </ResponsiveContainer>
              <div className="flex justify-between text-xs text-slate-500 mt-1 px-8">
                <span className="text-emerald-500">30 (oversold)</span>
                <span className="text-red-500">70 (overbought)</span>
              </div>
            </div>

            <div className="card">
              <p className="card-title">MACD</p>
              <ResponsiveContainer width="100%" height={130}>
                <ComposedChart data={techData} margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis dataKey="date" tick={false} />
                  <YAxis tick={{ fill: '#64748b', fontSize: 10 }} width={45} />
                  <Tooltip content={<ChartTooltip />} />
                  <ReferenceLine y={0} stroke="#475569" />
                  <Bar dataKey="macd_hist" fill="#3b82f6" opacity={0.6} name="hist" />
                  <Line type="monotone" dataKey="macd" stroke="#22c55e" strokeWidth={1.5} dot={false} name="macd" />
                  <Line type="monotone" dataKey="macd_signal" stroke="#f59e0b" strokeWidth={1.5} dot={false} name="signal" />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="card">
            <p className="card-title">Returns</p>
            {returnsLoading ? (
              <p className="text-sm text-slate-500">Loading returns…</p>
            ) : returnsData?.error ? (
              <p className="text-sm text-red-400">{returnsData.error}</p>
            ) : (
              <>
                <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-2 mb-4">
                  <MetricCard label="Mean" value={fmtNumber(returnsData?.stats?.mean, 6)} />
                  <MetricCard label="Std" value={fmtNumber(returnsData?.stats?.std, 6)} />
                  <MetricCard label="Var" value={fmtNumber(returnsData?.stats?.var, 6)} />
                  <MetricCard
                    label="Annual Return"
                    value={fmtPct(returnsData?.stats?.annual_return != null ? returnsData.stats.annual_return * 100 : null)}
                  />
                  <MetricCard
                    label="Annual Vol"
                    value={fmtPct(returnsData?.stats?.annual_volatility != null ? returnsData.stats.annual_volatility * 100 : null)}
                  />
                  <MetricCard label="Skewness" value={fmtNumber(returnsData?.stats?.skewness, 3)} />
                  <MetricCard label="Kurtosis" value={fmtNumber(returnsData?.stats?.kurtosis, 3)} />
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                  <div>
                    <p className="text-xs text-slate-500 mb-2">Log Return Histogram</p>
                    <ResponsiveContainer width="100%" height={220}>
                      <BarChart data={histogramRows}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                        <XAxis dataKey="bin" tick={{ fill: '#64748b', fontSize: 10 }} />
                        <YAxis tick={{ fill: '#64748b', fontSize: 10 }} />
                        <Tooltip content={<ChartTooltip />} />
                        <Bar dataKey="count" fill="#3b82f6" />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>

                  <div>
                    <p className="text-xs text-slate-500 mb-2">Daily Log Returns</p>
                    <ResponsiveContainer width="100%" height={220}>
                      <BarChart data={returnsData?.daily_returns || []}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                        <XAxis dataKey="date" tick={{ fill: '#64748b', fontSize: 10 }} tickFormatter={(d) => d.slice(5)} />
                        <YAxis tick={{ fill: '#64748b', fontSize: 10 }} />
                        <Tooltip content={<ChartTooltip />} />
                        <Bar dataKey="log" fill="#14b8a6" />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              </>
            )}
          </div>

          <div className="card">
            <p className="card-title">Recent Price Data</p>
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-slate-700">
                    {['Date', 'Open', 'High', 'Low', 'Close', 'Volume'].map((h) => (
                      <th key={h} className="th">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {priceData.slice(-10).reverse().map((row) => (
                    <tr key={row.date} className="table-row">
                      <td className="td text-slate-400">{row.date}</td>
                      <td className="td">{fmtCurrency(row.open)}</td>
                      <td className="td text-emerald-400">{fmtCurrency(row.high)}</td>
                      <td className="td text-red-400">{fmtCurrency(row.low)}</td>
                      <td className={`td font-semibold ${row.close >= row.open ? 'text-emerald-400' : 'text-red-400'}`}>
                        {fmtCurrency(row.close)}
                      </td>
                      <td className="td text-slate-400">{row.volume?.toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="card">
            <p className="card-title">News Sentiment</p>
            {sentimentLoading ? (
              <p className="text-sm text-slate-500">Loading sentiment…</p>
            ) : !sentimentData?.available ? (
              <p className="text-sm text-slate-500">
                {sentimentData?.message || 'News sentiment requires Alpha Vantage API key. Set datasource.alphavantage.secret in .env'}
              </p>
            ) : (
              <>
                <div className="flex flex-wrap items-center gap-2 mb-3">
                  <span className="badge bg-slate-700 text-slate-100">{sentimentData.overall_sentiment}</span>
                  <span className="text-sm text-slate-300">Score: {fmtNumber(sentimentData.overall_score, 3)}</span>
                  {sentimentData.total_articles != null && (
                    <span className="text-xs text-slate-500">Sample: {sentimentData.total_articles} articles</span>
                  )}
                </div>
                <div className="mb-4">
                  <ResponsiveContainer width="100%" height={220}>
                    <BarChart data={sentimentDistRows} layout="vertical" margin={{ top: 5, right: 12, left: 12, bottom: 5 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                      <XAxis type="number" tick={{ fill: '#64748b', fontSize: 10 }} />
                      <YAxis type="category" dataKey="label" tick={{ fill: '#64748b', fontSize: 10 }} width={110} />
                      <Tooltip content={<ChartTooltip />} />
                      <Bar dataKey="count" name="Articles">
                        {sentimentDistRows.map((entry) => (
                          <Cell key={entry.label} fill={entry.fill} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
                <div className="space-y-2">
                  {(sentimentData.articles || []).map((article, idx) => (
                    <a
                      key={`${article.url}-${idx}`}
                      href={article.url || '#'}
                      target="_blank"
                      rel="noreferrer"
                      className="block border border-slate-700 rounded-lg p-3 hover:bg-slate-700/30 transition-colors"
                    >
                      <p className="text-sm text-slate-100">{article.title || 'Untitled'}</p>
                      <p className="text-xs text-slate-500 mt-1">
                        {article.source || 'Unknown source'} · {article.published || 'N/A'} · {article.sentiment_label || 'N/A'}
                      </p>
                    </a>
                  ))}
                </div>
              </>
            )}
          </div>

          <GoogleTrends ticker={info.ticker} companyName={info.name} />
          <AthAnalysis ticker={info.ticker} />
          <AnalystSection ticker={info.ticker} />
          <EarningsEstimates ticker={info.ticker} />
          <FinancialStatements ticker={info.ticker} />
          <EpsTrend ticker={info.ticker} />
          <EconomicCycleSection ticker={info.ticker} />
          <FredRateChart />
          <PeerComparison ticker={info.ticker} />
        </>
      )}
    </div>
  )
}
