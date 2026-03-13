import { useEffect, useState } from 'react'
import { getEconomicCycle } from '../api/client'

const STATUS_STYLE = {
  favored: 'text-emerald-300 bg-emerald-900/40 border-emerald-700',
  neutral: 'text-slate-300 bg-slate-800 border-slate-700',
  stressed: 'text-red-300 bg-red-900/35 border-red-700',
}

export default function EconomicCycleSection({ ticker }) {
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
        const res = await getEconomicCycle(ticker)
        if (!ignore) setData(res.data)
      } catch (e) {
        if (!ignore) {
          setError(e.response?.data?.detail || 'Failed to load economic cycle context')
          setData(null)
        }
      } finally {
        if (!ignore) setLoading(false)
      }
    }

    run()
    return () => { ignore = true }
  }, [ticker])

  return (
    <div className="card">
      <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
        <p className="card-title !mb-0">Sector & Economic Cycle</p>
        {data?.cycle_proxy?.phase && (
          <span className="badge bg-blue-900/40 text-blue-300 border border-blue-700">
            Market Proxy: {data.cycle_proxy.phase}
          </span>
        )}
      </div>

      {loading && <p className="text-sm text-slate-500">Loading cycle context…</p>}
      {!loading && error && <p className="text-sm text-red-400">{error}</p>}

      {!loading && !error && data && (
        <>
          <p className="text-xs text-slate-500 mb-3">
            {data.ticker}: {data.sector || 'Unknown sector'}
            {data.industry ? ` · ${data.industry}` : ''}
          </p>

          <div className="overflow-x-auto">
            <table className="w-full min-w-[620px] text-xs">
              <thead>
                <tr className="border-b border-slate-700">
                  <th className="th">Phase</th>
                  <th className="th">Sector Bias</th>
                  <th className="th">Interpretation</th>
                </tr>
              </thead>
              <tbody>
                {(data.sector_cycle_matrix || []).map((row) => (
                  <tr key={row.phase} className="table-row">
                    <td className="td text-slate-200 font-medium">{row.phase}</td>
                    <td className="td">
                      <span className={`inline-flex px-2 py-0.5 rounded border ${STATUS_STYLE[row.status] || STATUS_STYLE.neutral}`}>
                        {row.status}
                      </span>
                    </td>
                    <td className="td text-slate-400">{data.phase_explanations?.[row.phase] || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="mt-3 text-xs text-slate-500">
            <p>
              Signals: S&P500 above 200D = {String(data.cycle_proxy?.signal?.sp500_above_200d)},
              Yield spread = {data.cycle_proxy?.signal?.yield_curve_spread ?? 'N/A'}
            </p>
          </div>
        </>
      )}
    </div>
  )
}
