import { useEffect, useState, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { Plus, Pencil, Trash2, RefreshCw, Search, TrendingUp } from 'lucide-react'
import { getHoldings, getPortfolios, addHolding, updateHolding, deleteHolding, getBatchSignals } from '../api/client'
import { fmtCurrency, fmtPct, fmtNumber, gainColor, assetTypeBadge, marketCapLabel } from '../utils/format'

const ASSET_TYPES = ['STOCK', 'ETF', 'BOND', 'FUND']

const EMPTY_FORM = {
  ticker: '', name: '', shares: '', avg_price: '',
  currency: 'USD', asset_type: 'STOCK', portfolio: '', exchange: '', notes: '',
}

function SignalBadges({ signal }) {
  if (!signal) return <span className="text-slate-600 text-xs">...</span>

  return (
    <div className="flex flex-col gap-1">
      <span className={`badge text-[10px] ${
        signal.trend === 'bullish' ? 'bg-emerald-900/50 text-emerald-400'
        : signal.trend === 'bearish' ? 'bg-red-900/50 text-red-400'
        : 'bg-slate-800 text-slate-500'
      }`}>
        {signal.trend === 'bullish' ? '↑ Bullish' : signal.trend === 'bearish' ? '↓ Bearish' : '→ Neutral'}
      </span>
      {signal.rsi_signal === 'overbought' && (
        <span className="badge text-[10px] bg-red-900/50 text-red-400">RSI {signal.rsi}</span>
      )}
      {signal.rsi_signal === 'oversold' && (
        <span className="badge text-[10px] bg-emerald-900/50 text-emerald-400">RSI {signal.rsi}</span>
      )}
    </div>
  )
}

function Modal({ title, onClose, onSubmit, form, setForm, portfolios, editing }) {
  const handleChange = (e) => setForm((f) => ({ ...f, [e.target.name]: e.target.value }))

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="card w-full max-w-lg mx-4">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-base font-semibold text-slate-100">{title}</h2>
          <button onClick={onClose} className="text-slate-500 hover:text-slate-300 text-xl leading-none">×</button>
        </div>

        <form onSubmit={onSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label">Ticker *</label>
              <input
                name="ticker" value={form.ticker} onChange={handleChange}
                className="input uppercase" placeholder="AAPL" required
                disabled={editing}
              />
            </div>
            <div>
              <label className="label">Name</label>
              <input name="name" value={form.name} onChange={handleChange} className="input" placeholder="Auto-detect" />
            </div>
            <div>
              <label className="label">Shares *</label>
              <input name="shares" value={form.shares} onChange={handleChange} className="input" type="number" step="any" required />
            </div>
            <div>
              <label className="label">Avg. Price *</label>
              <input name="avg_price" value={form.avg_price} onChange={handleChange} className="input" type="number" step="any" required />
            </div>
            <div>
              <label className="label">Asset Type *</label>
              <select name="asset_type" value={form.asset_type} onChange={handleChange} className="select">
                {ASSET_TYPES.map((t) => <option key={t}>{t}</option>)}
              </select>
            </div>
            <div>
              <label className="label">Currency</label>
              <input name="currency" value={form.currency} onChange={handleChange} className="input" placeholder="USD" />
            </div>
            <div>
              <label className="label">Portfolio</label>
              <select name="portfolio" value={form.portfolio} onChange={handleChange} className="select">
                <option value="">— None —</option>
                {portfolios.map((p) => <option key={p.id} value={p.name}>{p.name}</option>)}
              </select>
            </div>
            <div>
              <label className="label">Exchange</label>
              <input name="exchange" value={form.exchange} onChange={handleChange} className="input" placeholder="NASDAQ" />
            </div>
          </div>
          <div>
            <label className="label">Notes</label>
            <textarea name="notes" value={form.notes} onChange={handleChange} className="input" rows={2} />
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={onClose} className="btn-ghost">Cancel</button>
            <button type="submit" className="btn-primary">
              {editing ? 'Save Changes' : 'Add Holding'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default function Holdings() {
  const [holdings, setHoldings] = useState([])
  const [portfolios, setPortfolios] = useState([])
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [editTarget, setEditTarget] = useState(null)
  const [form, setForm] = useState(EMPTY_FORM)
  const [filter, setFilter] = useState({ search: '', type: '', portfolio: '' })
  const [sortKey, setSortKey] = useState('ticker')
  const [sortDir, setSortDir] = useState(1)
  const [signals, setSignals] = useState({})

  const load = useCallback(() => {
    setLoading(true)
    Promise.all([getHoldings(), getPortfolios()])
      .then(([h, p]) => {
        setHoldings(h.data)
        setPortfolios(p.data)
        // Auto-fetch signals for all tickers
        const tickers = [...new Set(h.data.map((x) => x.ticker))]
        if (tickers.length > 0) {
          getBatchSignals(tickers.join(','))
            .then((res) => {
              const map = {}
              for (const sig of res.data) map[sig.ticker] = sig
              setSignals(map)
            })
            .catch(() => {})
        }
      })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { load() }, [load])

  const openAdd = () => { setForm(EMPTY_FORM); setEditTarget(null); setShowModal(true) }
  const openEdit = (h) => {
    setForm({
      ticker: h.ticker, name: h.name || '', shares: h.shares,
      avg_price: h.avg_price, currency: h.currency,
      asset_type: h.asset_type, portfolio: h.portfolio || '',
      exchange: h.exchange || '', notes: h.notes || '',
    })
    setEditTarget(h.id)
    setShowModal(true)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    const payload = {
      ...form,
      shares: parseFloat(form.shares),
      avg_price: parseFloat(form.avg_price),
    }
    try {
      if (editTarget) await updateHolding(editTarget, payload)
      else await addHolding(payload)
      setShowModal(false)
      load()
    } catch (err) {
      alert(err.response?.data?.detail || 'Error saving holding')
    }
  }

  const handleDelete = async (id, ticker) => {
    if (!confirm(`Delete ${ticker}?`)) return
    await deleteHolding(id)
    load()
  }

  const toggleSort = (key) => {
    if (sortKey === key) setSortDir((d) => -d)
    else { setSortKey(key); setSortDir(1) }
  }

  const filtered = holdings
    .filter((h) => {
      const q = filter.search.toLowerCase()
      const matchSearch = !q || h.ticker.toLowerCase().includes(q) || (h.name || '').toLowerCase().includes(q)
      const matchType = !filter.type || h.asset_type === filter.type
      const matchPort = !filter.portfolio || h.portfolio === filter.portfolio
      return matchSearch && matchType && matchPort
    })
    .sort((a, b) => {
      const va = a[sortKey] ?? ''
      const vb = b[sortKey] ?? ''
      return va < vb ? -sortDir : va > vb ? sortDir : 0
    })

  const totalValue = filtered.reduce((s, h) => s + (h.current_value ?? h.cost_basis), 0)
  const totalCost  = filtered.reduce((s, h) => s + h.cost_basis, 0)
  const totalGL    = totalValue - totalCost

  const SortTh = ({ label, k }) => (
    <th className="th cursor-pointer select-none hover:text-slate-200" onClick={() => toggleSort(k)}>
      {label} {sortKey === k ? (sortDir > 0 ? '↑' : '↓') : ''}
    </th>
  )

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-slate-100">Holdings</h1>
        <div className="flex gap-2">
          <button onClick={load} className="btn-ghost"><RefreshCw size={15} /></button>
          <button onClick={openAdd} className="btn-primary"><Plus size={15} /> Add</button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 items-center">
        <div className="relative">
          <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-500" />
          <input
            className="input pl-8 w-48"
            placeholder="Search ticker / name…"
            value={filter.search}
            onChange={(e) => setFilter((f) => ({ ...f, search: e.target.value }))}
          />
        </div>
        <select className="select w-36" value={filter.type} onChange={(e) => setFilter((f) => ({ ...f, type: e.target.value }))}>
          <option value="">All Types</option>
          {ASSET_TYPES.map((t) => <option key={t}>{t}</option>)}
        </select>
        <select className="select w-40" value={filter.portfolio} onChange={(e) => setFilter((f) => ({ ...f, portfolio: e.target.value }))}>
          <option value="">All Portfolios</option>
          {portfolios.map((p) => <option key={p.id} value={p.name}>{p.name}</option>)}
        </select>
      </div>

      {/* Summary bar */}
      {filtered.length > 0 && (
        <div className="flex gap-6 px-4 py-3 bg-slate-800/50 rounded-lg border border-slate-700 text-sm">
          <span className="text-slate-400">{filtered.length} positions</span>
          <span>Value: <strong className="text-slate-100">{fmtCurrency(totalValue)}</strong></span>
          <span>Cost: <strong className="text-slate-100">{fmtCurrency(totalCost)}</strong></span>
          <span className={gainColor(totalGL)}>
            P&L: <strong>{fmtCurrency(totalGL)} ({fmtPct(totalCost ? totalGL / totalCost * 100 : 0)})</strong>
          </span>
        </div>
      )}

      {/* Table */}
      <div className="card !p-0 overflow-x-auto">
        <table className="w-full min-w-[940px]">
          <thead className="border-b border-slate-700">
            <tr>
              <SortTh label="Ticker" k="ticker" />
              <SortTh label="Name" k="name" />
              <th className="th">Type</th>
              <SortTh label="Portfolio" k="portfolio" />
              <SortTh label="Shares" k="shares" />
              <SortTh label="Avg Price" k="avg_price" />
              <SortTh label="Cur. Price" k="current_price" />
              <th className="th">Signal</th>
              <SortTh label="Value" k="current_value" />
              <SortTh label="P&L" k="gain_loss" />
              <SortTh label="P&L %" k="gain_loss_pct" />
              <th className="th">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={12} className="td text-center text-slate-500 py-12">Loading…</td></tr>
            ) : filtered.length === 0 ? (
              <tr><td colSpan={12} className="td text-center text-slate-500 py-12">No holdings found.</td></tr>
            ) : (
              filtered.map((h) => {
                const capTag = h.asset_type === 'STOCK'
                  ? marketCapLabel(h.market_cap_usd ?? h.market_cap)
                  : null
                return (
                  <tr key={h.id} className="table-row">
                    <td className="td font-mono font-semibold text-blue-400">
                      <Link to={`/stocks/${h.ticker}`} className="hover:underline">{h.ticker}</Link>
                    </td>
                    <td className="td text-slate-300 max-w-[220px]">
                      <div className="flex items-center gap-2">
                        <span className="truncate">{h.name}</span>
                        {capTag && <span className={`badge text-[10px] ${capTag.color}`}>{capTag.label}</span>}
                      </div>
                    </td>
                    <td className="td">
                      <span className={`badge ${assetTypeBadge(h.asset_type)}`}>{h.asset_type}</span>
                    </td>
                    <td className="td text-slate-400">{h.portfolio || '—'}</td>
                    <td className="td text-right">{fmtNumber(h.shares, 4)}</td>
                    <td className="td text-right">{fmtCurrency(h.avg_price)}</td>
                    <td className="td text-right">{h.current_price ? fmtCurrency(h.current_price) : <span className="text-slate-600">—</span>}</td>
                    <td className="td">
                      <SignalBadges signal={signals[h.ticker]} />
                    </td>
                    <td className="td text-right font-medium">{fmtCurrency(h.current_value ?? h.cost_basis)}</td>
                    <td className={`td text-right font-medium ${gainColor(h.gain_loss)}`}>
                      {fmtCurrency(h.gain_loss)}
                    </td>
                    <td className={`td text-right font-medium ${gainColor(h.gain_loss_pct)}`}>
                      {fmtPct(h.gain_loss_pct)}
                    </td>
                    <td className="td">
                      <div className="flex items-center gap-1">
                        <Link to={`/stocks/${h.ticker}`} className="btn-ghost !px-2 !py-1" title="Analyze">
                          <TrendingUp size={13} />
                        </Link>
                        <button onClick={() => openEdit(h)} className="btn-ghost !px-2 !py-1">
                          <Pencil size={13} />
                        </button>
                        <button onClick={() => handleDelete(h.id, h.ticker)} className="btn-danger !px-2 !py-1">
                          <Trash2 size={13} />
                        </button>
                      </div>
                    </td>
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
      </div>

      {showModal && (
        <Modal
          title={editTarget ? 'Edit Holding' : 'Add Holding'}
          onClose={() => setShowModal(false)}
          onSubmit={handleSubmit}
          form={form}
          setForm={setForm}
          portfolios={portfolios}
          editing={!!editTarget}
        />
      )}
    </div>
  )
}
