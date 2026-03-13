import { useEffect, useState } from 'react'
import { getAthAnalysis } from '../api/client'
import { fmtCurrency, fmtPct, gainColor } from '../utils/format'

function MetricCard({ label, value, color = '' }) {
  return (
    <div className="bg-slate-900 border border-slate-700 rounded-lg p-3">
      <p className="text-xs text-slate-500 mb-1">{label}</p>
      <p className={`text-base font-semibold ${color || 'text-slate-100'}`}>{value}</p>
    </div>
  )
}

function clamp(v) {
  if (!Number.isFinite(v)) return 0
  if (v < 0) return 0
  if (v > 100) return 100
  return v
}

export default function AthAnalysis({ ticker }) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [data, setData] = useState(null)

  useEffect(() => {
    if (!ticker) return
    let ignore = false

    const run = async () => {
      setLoading(true)
      setError('')
      try {
        const res = await getAthAnalysis(ticker)
        if (!ignore) setData(res.data)
      } catch (e) {
        if (!ignore) {
          setError(e.response?.data?.detail || 'Failed to load ATH analysis')
          setData(null)
        }
      } finally {
        if (!ignore) setLoading(false)
      }
    }

    run()
    return () => { ignore = true }
  }, [ticker])

  const down = data?.down_from_ath_pct
  const rangePosition = clamp(data?.range_position)
  const hasRange = Number.isFinite(data?.all_time_high) && Number.isFinite(data?.all_time_low) && data.all_time_high > data.all_time_low

  const downColor = !Number.isFinite(down)
    ? 'text-slate-200'
    : down < 20
      ? 'text-emerald-400'
      : down <= 50
        ? 'text-amber-400'
        : 'text-red-400'

  return (
    <div className="card">
      <p className="card-title">ATH Drawdown Analysis</p>

      {loading && <p className="text-sm text-slate-500">Loading ATH analysis…</p>}
      {!loading && error && <p className="text-sm text-red-400">{error}</p>}
      {!loading && !error && data?.error && !Number.isFinite(data?.all_time_high) && (
        <p className="text-sm text-slate-500">{data.error}</p>
      )}

      {!loading && !error && data && Number.isFinite(data?.all_time_high) && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-3">
            <MetricCard
              label={`All-Time High${data?.ath_date ? ` (${data.ath_date})` : ''}`}
              value={fmtCurrency(data?.all_time_high)}
            />
            <MetricCard
              label={`All-Time Low${data?.atl_date ? ` (${data.atl_date})` : ''}`}
              value={fmtCurrency(data?.all_time_low)}
            />
            <MetricCard label="Current Price" value={fmtCurrency(data?.current_price)} />
            <MetricCard
              label="Down From ATH"
              value={fmtPct(down)}
              color={downColor}
            />
          </div>

          {hasRange ? (
            <div>
              <div className="flex items-center justify-between text-xs mb-1 text-slate-400">
                <span>Price position in ATL-ATH range</span>
                <span>{fmtPct(rangePosition, 1)}</span>
              </div>
              <div className="relative h-8 rounded bg-slate-800 border border-slate-700 overflow-hidden">
                <div className="absolute inset-y-0 left-0 bg-slate-700/70" style={{ width: `${rangePosition}%` }} />
                <div className="absolute top-1/2 -translate-y-1/2" style={{ left: `${rangePosition}%` }}>
                  <div className="w-2.5 h-2.5 rounded-full bg-blue-400 border border-slate-900 -ml-1" />
                </div>
              </div>
              <div className="mt-1 flex justify-between text-[11px] text-slate-500">
                <span>ATL {fmtCurrency(data?.all_time_low)}</span>
                <span className={gainColor(data?.up_from_atl_pct)}>{fmtPct(data?.up_from_atl_pct, 1)} from ATL</span>
                <span>ATH {fmtCurrency(data?.all_time_high)}</span>
              </div>
            </div>
          ) : (
            <p className="text-xs text-slate-500">Range position is unavailable for this ticker.</p>
          )}
        </div>
      )}
    </div>
  )
}
