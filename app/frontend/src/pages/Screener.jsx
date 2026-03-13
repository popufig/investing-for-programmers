import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { ChevronDown, Plus, Search, Settings, X } from 'lucide-react'
import {
  addToWatchlist,
  addUniverseTickers,
  getScreenOptions,
  getUniverse,
  removeUniverseTicker,
  screenStocks,
} from '../api/client'
import { fmtCurrency, fmtPct, fmtNumber } from '../utils/format'

/* ── Multi-select dropdown ─────────────────────────────────────── */
function MultiSelect({ label, options, selected, onChange }) {
  const [open, setOpen] = useState(false)
  const ref = useRef(null)

  useEffect(() => {
    const handler = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const toggle = (val) => {
    if (selected.includes(val)) onChange(selected.filter((s) => s !== val))
    else onChange([...selected, val])
  }

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        className="select w-full flex items-center justify-between gap-1 text-left"
        onClick={() => setOpen((o) => !o)}
      >
        <span className="truncate text-sm">
          {selected.length === 0
            ? label
            : selected.length <= 2
              ? selected.join(', ')
              : `${selected.length} selected`}
        </span>
        <ChevronDown size={14} className={`shrink-0 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>

      {open && (
        <div className="absolute z-40 mt-1 w-full max-h-60 overflow-y-auto bg-slate-800 border border-slate-600 rounded-lg shadow-xl">
          {selected.length > 0 && (
            <button
              type="button"
              className="w-full px-3 py-1.5 text-xs text-slate-400 hover:bg-slate-700 text-left border-b border-slate-700"
              onClick={() => { onChange([]); setOpen(false) }}
            >
              Clear all
            </button>
          )}
          {options.map((opt) => (
            <label
              key={opt}
              className="flex items-center gap-2 px-3 py-1.5 hover:bg-slate-700 cursor-pointer text-sm text-slate-300"
            >
              <input
                type="checkbox"
                checked={selected.includes(opt)}
                onChange={() => toggle(opt)}
                className="accent-blue-500"
              />
              {opt}
            </label>
          ))}
          {options.length === 0 && (
            <p className="px-3 py-2 text-xs text-slate-500">No options</p>
          )}
        </div>
      )}
    </div>
  )
}

/* ── Screener page ─────────────────────────────────────────────── */
const EMPTY_FILTERS = {
  sectors: [],
  industries: [],
  countries: [],
  market_cap_min: '',
  market_cap_max: '',
  pe_min: '',
  pe_max: '',
  dividend_yield_min: '',
  change_52w_min: '',
}

export default function Screener() {
  const [filters, setFilters] = useState(EMPTY_FILTERS)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState({ total: 0, filters_applied: {}, results: [] })

  const [options, setOptions] = useState({ sectors: [], industries: [], countries: [] })
  const [optionsLoading, setOptionsLoading] = useState(true)

  const [showUniverse, setShowUniverse] = useState(false)
  const [universe, setUniverse] = useState([])
  const [universeLoading, setUniverseLoading] = useState(false)
  const [addInput, setAddInput] = useState('')

  useEffect(() => {
    setOptionsLoading(true)
    getScreenOptions()
      .then((res) => setOptions(res.data || { sectors: [], industries: [], countries: [] }))
      .catch(() => {})
      .finally(() => setOptionsLoading(false))
  }, [])

  const reloadOptions = () => {
    getScreenOptions()
      .then((res) => setOptions(res.data || { sectors: [], industries: [], countries: [] }))
      .catch(() => {})
  }

  const loadUniverse = () => {
    setUniverseLoading(true)
    getUniverse()
      .then((res) => setUniverse(res.data || []))
      .catch(() => {})
      .finally(() => setUniverseLoading(false))
  }

  const openUniverse = () => {
    setShowUniverse(true)
    loadUniverse()
  }

  const handleAddTickers = async (e) => {
    e.preventDefault()
    const tickers = addInput.split(/[,\s]+/).map((s) => s.trim().toUpperCase()).filter(Boolean)
    if (tickers.length === 0) return
    try {
      const res = await addUniverseTickers(tickers)
      if (res.data.added.length > 0) {
        loadUniverse()
        reloadOptions()
      }
      setAddInput('')
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to add tickers')
    }
  }

  const handleRemoveTicker = async (ticker) => {
    try {
      await removeUniverseTicker(ticker)
      setUniverse((prev) => prev.filter((r) => r.ticker !== ticker))
      reloadOptions()
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to remove')
    }
  }

  const runScreen = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const params = {}
      if (filters.sectors.length) params.sector = filters.sectors.join(',')
      if (filters.industries.length) params.industry = filters.industries.join(',')
      if (filters.countries.length) params.country = filters.countries.join(',')
      for (const k of ['market_cap_min', 'market_cap_max', 'pe_min', 'pe_max', 'dividend_yield_min', 'change_52w_min']) {
        if (filters[k] !== '') params[k] = Number(filters[k])
      }
      const res = await screenStocks(params)
      setResult(res.data || { total: 0, filters_applied: {}, results: [] })
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to run screener')
      setResult({ total: 0, filters_applied: {}, results: [] })
    } finally {
      setLoading(false)
    }
  }

  const addWatch = async (ticker) => {
    try {
      await addToWatchlist({ ticker })
      alert(`Added ${ticker} to watchlist`)
    } catch (e) {
      alert(e.response?.data?.detail || `Failed to add ${ticker}`)
    }
  }

  const setField = (key, value) => setFilters((f) => ({ ...f, [key]: value }))

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-slate-100">Stock Screener</h1>
        <button className="btn-ghost !px-4 !py-2 whitespace-nowrap" onClick={openUniverse} title="Manage Stock Pool">
          <Settings size={15} /> Manage Stock Pool
        </button>
      </div>

      <div className="card">
        <form className="grid grid-cols-1 md:grid-cols-3 gap-3" onSubmit={runScreen}>
          <MultiSelect
            label="All Sectors"
            options={options.sectors}
            selected={filters.sectors}
            onChange={(v) => setField('sectors', v)}
          />
          <MultiSelect
            label="All Industries"
            options={options.industries}
            selected={filters.industries}
            onChange={(v) => setField('industries', v)}
          />
          <MultiSelect
            label="All Countries"
            options={options.countries}
            selected={filters.countries}
            onChange={(v) => setField('countries', v)}
          />

          <input className="input" type="number" step="any" placeholder="Market Cap Min" value={filters.market_cap_min} onChange={(e) => setField('market_cap_min', e.target.value)} />
          <input className="input" type="number" step="any" placeholder="Market Cap Max" value={filters.market_cap_max} onChange={(e) => setField('market_cap_max', e.target.value)} />
          <input className="input" type="number" step="any" placeholder="P/E Min" value={filters.pe_min} onChange={(e) => setField('pe_min', e.target.value)} />

          <input className="input" type="number" step="any" placeholder="P/E Max" value={filters.pe_max} onChange={(e) => setField('pe_max', e.target.value)} />
          <input className="input" type="number" step="any" placeholder="Dividend Yield Min (0.02)" value={filters.dividend_yield_min} onChange={(e) => setField('dividend_yield_min', e.target.value)} />
          <input className="input" type="number" step="any" placeholder="52w Change Min (0.1)" value={filters.change_52w_min} onChange={(e) => setField('change_52w_min', e.target.value)} />

          <div className="md:col-span-3 flex gap-2">
            <button className="btn-primary" type="submit" disabled={loading}>
              <Search size={14} />
              {loading ? 'Screening…' : 'Run Screener'}
            </button>
            <button type="button" className="btn-ghost" onClick={() => setFilters(EMPTY_FILTERS)}>
              Reset
            </button>
          </div>
        </form>
      </div>

      {!!error && <p className="text-sm text-red-400">{error}</p>}

      <div className="card !p-0 overflow-x-auto">
        <div className="px-5 py-3 border-b border-slate-700 text-sm text-slate-400">
          Results: <span className="text-slate-100 font-semibold">{result.total}</span>
        </div>
        <table className="w-full min-w-[1050px]">
          <thead className="border-b border-slate-700">
            <tr>
              <th className="th">Ticker</th>
              <th className="th">Name</th>
              <th className="th">Sector</th>
              <th className="th">Industry</th>
              <th className="th">Country</th>
              <th className="th text-right">Market Cap</th>
              <th className="th text-right">P/E</th>
              <th className="th text-right">Div Yield</th>
              <th className="th text-right">52w Change</th>
              <th className="th text-right">Price</th>
              <th className="th">Action</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td className="td text-center text-slate-500 py-10" colSpan={11}>Loading…</td></tr>
            ) : result.results.length === 0 ? (
              <tr><td className="td text-center text-slate-500 py-10" colSpan={11}>No results.</td></tr>
            ) : (
              result.results.map((row) => (
                <tr key={row.ticker} className="table-row">
                  <td className="td font-mono font-semibold text-blue-400">
                    <Link to={`/stocks/${row.ticker}`} className="hover:underline">{row.ticker}</Link>
                  </td>
                  <td className="td text-slate-300">{row.name || row.ticker}</td>
                  <td className="td text-slate-400">{row.sector || '—'}</td>
                  <td className="td text-slate-400">{row.industry || '—'}</td>
                  <td className="td text-slate-400">{row.country || '—'}</td>
                  <td className="td text-right">{fmtCurrency(row.market_cap)}</td>
                  <td className="td text-right">{fmtNumber(row.pe_ratio, 2)}</td>
                  <td className="td text-right">{fmtPct(row.dividend_yield != null ? row.dividend_yield * 100 : null)}</td>
                  <td className={`td text-right ${row.change_52w >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                    {fmtPct(row.change_52w != null ? row.change_52w * 100 : null)}
                  </td>
                  <td className="td text-right">{fmtCurrency(row.price)}</td>
                  <td className="td">
                    <button className="btn-ghost !px-2 !py-1" onClick={() => addWatch(row.ticker)}>
                      <Plus size={13} /> Watch
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Universe Management Modal */}
      {showUniverse && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="card w-full max-w-2xl mx-4 max-h-[80vh] flex flex-col">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-base font-semibold text-slate-100">
                Stock Pool ({universe.length} tickers)
              </h2>
              <button onClick={() => setShowUniverse(false)} className="text-slate-500 hover:text-slate-300">
                <X size={18} />
              </button>
            </div>

            <form className="flex gap-2 mb-4" onSubmit={handleAddTickers}>
              <input
                className="input flex-1 uppercase"
                placeholder="Add tickers (e.g. PLTR, COIN, SOFI)"
                value={addInput}
                onChange={(e) => setAddInput(e.target.value)}
              />
              <button className="btn-primary" type="submit">
                <Plus size={14} /> Add
              </button>
            </form>

            <div className="overflow-y-auto flex-1 border border-slate-700 rounded-lg">
              {universeLoading ? (
                <p className="text-center text-slate-500 py-8">Loading…</p>
              ) : (
                <div className="flex flex-wrap gap-1.5 p-3">
                  {universe.map((r) => (
                    <span
                      key={r.ticker}
                      className="inline-flex items-center gap-1 px-2.5 py-1.5 bg-slate-800 border border-slate-700 rounded text-xs font-mono text-slate-300 hover:border-slate-500 group"
                    >
                      {r.ticker}
                      <button
                        onClick={() => handleRemoveTicker(r.ticker)}
                        className="text-slate-600 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-opacity"
                        title="Remove"
                      >
                        <X size={12} />
                      </button>
                    </span>
                  ))}
                </div>
              )}
            </div>

            <p className="text-xs text-slate-600 mt-3">
              Add or remove tickers from the screener stock pool. Changes take effect on the next screen run.
            </p>
          </div>
        </div>
      )}
    </div>
  )
}
