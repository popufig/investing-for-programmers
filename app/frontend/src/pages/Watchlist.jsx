import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Plus, Pencil, Trash2, ArrowRightLeft, TrendingUp } from 'lucide-react'
import {
  addToWatchlist,
  convertToHolding,
  getBatchSignals,
  getPortfolios,
  getWatchlist,
  removeFromWatchlist,
  updateWatchlistItem,
} from '../api/client'
import { fmtCurrency, fmtPct } from '../utils/format'

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

function EditModal({ row, onClose, onSave }) {
  const [notes, setNotes] = useState(row.notes || '')
  const [target, setTarget] = useState(row.target_price ?? '')

  const submit = async (e) => {
    e.preventDefault()
    await onSave({
      notes: notes || null,
      target_price: target === '' ? null : Number(target),
    })
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="card w-full max-w-lg mx-4">
        <h2 className="text-base font-semibold text-slate-100 mb-4">Edit Watchlist Item</h2>
        <form className="space-y-3" onSubmit={submit}>
          <div>
            <label className="label">Ticker</label>
            <input className="input uppercase" value={row.ticker} disabled />
          </div>
          <div>
            <label className="label">Target Price</label>
            <input className="input" type="number" step="any" value={target} onChange={(e) => setTarget(e.target.value)} />
          </div>
          <div>
            <label className="label">Notes</label>
            <textarea className="input" rows={3} value={notes} onChange={(e) => setNotes(e.target.value)} />
          </div>
          <div className="flex justify-end gap-2">
            <button type="button" className="btn-ghost" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn-primary">Save</button>
          </div>
        </form>
      </div>
    </div>
  )
}

function ConvertModal({ row, portfolios, onClose, onConvert }) {
  const [shares, setShares] = useState('')
  const [avgPrice, setAvgPrice] = useState(row.current_price || row.target_price || '')
  const [portfolio, setPortfolio] = useState('')

  const submit = async (e) => {
    e.preventDefault()
    await onConvert({
      shares: Number(shares),
      avg_price: Number(avgPrice),
      portfolio: portfolio || null,
    })
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="card w-full max-w-lg mx-4">
        <h2 className="text-base font-semibold text-slate-100 mb-4">Move to Holdings: {row.ticker}</h2>
        <form className="space-y-3" onSubmit={submit}>
          <div>
            <label className="label">Shares *</label>
            <input className="input" type="number" step="any" required value={shares} onChange={(e) => setShares(e.target.value)} />
          </div>
          <div>
            <label className="label">Avg Price *</label>
            <input className="input" type="number" step="any" required value={avgPrice} onChange={(e) => setAvgPrice(e.target.value)} />
          </div>
          <div>
            <label className="label">Portfolio</label>
            <select className="select" value={portfolio} onChange={(e) => setPortfolio(e.target.value)}>
              <option value="">— None —</option>
              {portfolios.map((p) => (
                <option key={p.id} value={p.name}>{p.name}</option>
              ))}
            </select>
          </div>
          <div className="flex justify-end gap-2">
            <button type="button" className="btn-ghost" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn-primary">Convert</button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default function Watchlist() {
  const [rows, setRows] = useState([])
  const [portfolios, setPortfolios] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [form, setForm] = useState({ ticker: '', target_price: '', notes: '' })
  const [editRow, setEditRow] = useState(null)
  const [convertRow, setConvertRow] = useState(null)
  const [signals, setSignals] = useState({})

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [watchRes, portRes] = await Promise.all([getWatchlist(), getPortfolios()])
      const watchRows = watchRes.data || []
      setRows(watchRows)
      setPortfolios(portRes.data || [])
      // Auto-fetch signals for all tickers
      const tickers = [...new Set(watchRows.map((r) => r.ticker))]
      if (tickers.length > 0) {
        getBatchSignals(tickers.join(','))
          .then((res) => {
            const map = {}
            for (const sig of res.data) map[sig.ticker] = sig
            setSignals(map)
          })
          .catch(() => {})
      }
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to load watchlist')
      setRows([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const addItem = async (e) => {
    e.preventDefault()
    try {
      await addToWatchlist({
        ticker: form.ticker.toUpperCase().trim(),
        target_price: form.target_price === '' ? null : Number(form.target_price),
        notes: form.notes || null,
      })
      setForm({ ticker: '', target_price: '', notes: '' })
      await load()
    } catch (e2) {
      alert(e2.response?.data?.detail || 'Failed to add watchlist item')
    }
  }

  const removeItem = async (row) => {
    if (!confirm(`Remove ${row.ticker} from watchlist?`)) return
    try {
      await removeFromWatchlist(row.id)
      await load()
    } catch (e) {
      alert(e.response?.data?.detail || 'Failed to remove')
    }
  }

  const saveEdit = async (payload) => {
    if (!editRow) return
    try {
      await updateWatchlistItem(editRow.id, payload)
      setEditRow(null)
      await load()
    } catch (e) {
      alert(e.response?.data?.detail || 'Failed to update')
    }
  }

  const runConvert = async (payload) => {
    if (!convertRow) return
    try {
      await convertToHolding(convertRow.id, payload)
      setConvertRow(null)
      await load()
    } catch (e) {
      alert(e.response?.data?.detail || 'Failed to convert')
    }
  }

  return (
    <div className="p-6 space-y-5">
      <h1 className="text-xl font-semibold text-slate-100">Watchlist</h1>

      <div className="card">
        <p className="card-title">Add to Watchlist</p>
        <form className="grid grid-cols-1 md:grid-cols-4 gap-3" onSubmit={addItem}>
          <input
            className="input uppercase"
            placeholder="Ticker (e.g. SMR)"
            required
            value={form.ticker}
            onChange={(e) => setForm((f) => ({ ...f, ticker: e.target.value }))}
          />
          <input
            className="input"
            type="number"
            step="any"
            placeholder="Target Price (optional)"
            value={form.target_price}
            onChange={(e) => setForm((f) => ({ ...f, target_price: e.target.value }))}
          />
          <input
            className="input"
            placeholder="Notes (optional)"
            value={form.notes}
            onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
          />
          <button className="btn-primary" type="submit">
            <Plus size={14} /> Add
          </button>
        </form>
      </div>

      <div className="card !p-0 overflow-x-auto">
        <table className="w-full min-w-[1020px]">
          <thead className="border-b border-slate-700">
            <tr>
              <th className="th">Ticker</th>
              <th className="th">Name</th>
              <th className="th text-right">Price</th>
              <th className="th text-right">Change %</th>
              <th className="th">Signal</th>
              <th className="th">Sector</th>
              <th className="th text-right">Target</th>
              <th className="th">Notes</th>
              <th className="th">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td className="td text-center text-slate-500 py-12" colSpan={9}>Loading…</td></tr>
            ) : rows.length === 0 ? (
              <tr><td className="td text-center text-slate-500 py-12" colSpan={9}>Watchlist is empty.</td></tr>
            ) : rows.map((row) => {
              const hitTarget = row.target_price != null && row.current_price != null && row.current_price <= row.target_price
              return (
                <tr key={row.id} className="table-row">
                  <td className="td font-mono font-semibold text-blue-400">
                    <Link to={`/stocks/${row.ticker}`} className="hover:underline">{row.ticker}</Link>
                  </td>
                  <td className="td text-slate-300">{row.name || row.ticker}</td>
                  <td className="td text-right">{fmtCurrency(row.current_price)}</td>
                  <td className={`td text-right ${row.change_pct >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                    {fmtPct(row.change_pct)}
                  </td>
                  <td className="td">
                    <SignalBadges signal={signals[row.ticker]} />
                  </td>
                  <td className="td text-slate-400">{row.sector || '—'}</td>
                  <td className={`td text-right ${hitTarget ? 'text-emerald-400 font-semibold' : ''}`}>
                    {fmtCurrency(row.target_price)}
                  </td>
                  <td className="td text-slate-400">{row.notes || '—'}</td>
                  <td className="td">
                    <div className="flex items-center gap-1">
                      <Link to={`/stocks/${row.ticker}`} className="btn-ghost !px-2 !py-1" title="Analyze">
                        <TrendingUp size={13} />
                      </Link>
                      <button className="btn-ghost !px-2 !py-1" onClick={() => setEditRow(row)}>
                        <Pencil size={13} />
                      </button>
                      <button className="btn-ghost !px-2 !py-1" onClick={() => setConvertRow(row)}>
                        <ArrowRightLeft size={13} />
                      </button>
                      <button className="btn-danger !px-2 !py-1" onClick={() => removeItem(row)}>
                        <Trash2 size={13} />
                      </button>
                    </div>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {!!error && <p className="text-sm text-red-400">{error}</p>}

      {editRow && <EditModal row={editRow} onClose={() => setEditRow(null)} onSave={saveEdit} />}
      {convertRow && (
        <ConvertModal
          row={convertRow}
          portfolios={portfolios}
          onClose={() => setConvertRow(null)}
          onConvert={runConvert}
        />
      )}
    </div>
  )
}
