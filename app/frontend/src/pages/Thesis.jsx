import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, Plus, RefreshCw, Save, Trash2 } from 'lucide-react'
import {
  addThesisCheckpoint,
  createThesis,
  deleteThesis,
  getTheses,
  getThesis,
  getThesisSnapshot,
  updateThesis,
} from '../api/client'
import { fmtCurrency, fmtPct, gainColor } from '../utils/format'

const STATUSES = ['active', 'validated', 'invalidated', 'archived']
const CHECKPOINT_STATUSES = ['on_track', 'at_risk', 'invalidated']

const STATUS_STYLE = {
  active: 'bg-blue-900/40 text-blue-300 border-blue-700',
  validated: 'bg-emerald-900/40 text-emerald-300 border-emerald-700',
  invalidated: 'bg-red-900/40 text-red-300 border-red-700',
  archived: 'bg-slate-700 text-slate-300 border-slate-600',
  on_track: 'bg-emerald-900/40 text-emerald-300 border-emerald-700',
  at_risk: 'bg-amber-900/40 text-amber-300 border-amber-700',
}

function fmtDate(ts) {
  if (!ts) return '—'
  const d = new Date(ts)
  if (Number.isNaN(d.getTime())) return String(ts)
  return d.toLocaleString()
}

function toTickerInput(tickers) {
  return (tickers || []).map((t) => t.ticker).join(', ')
}

function normalizeTickerInput(text) {
  return text
    .split(',')
    .map((t) => t.trim().toUpperCase())
    .filter(Boolean)
    .filter((v, i, arr) => arr.indexOf(v) === i)
}

function StatusBadge({ status }) {
  return (
    <span className={`badge border ${STATUS_STYLE[status] || STATUS_STYLE.active}`}>
      {status}
    </span>
  )
}

export default function Thesis() {
  const navigate = useNavigate()
  const { id } = useParams()

  const [statusFilter, setStatusFilter] = useState('')
  const [listLoading, setListLoading] = useState(false)
  const [list, setList] = useState([])
  const [listError, setListError] = useState('')

  const [showCreate, setShowCreate] = useState(false)
  const [createForm, setCreateForm] = useState({
    title: '',
    summary: '',
    tickersInput: '',
    category: 'macro',
    targetDate: '',
  })

  const [detailLoading, setDetailLoading] = useState(false)
  const [detailError, setDetailError] = useState('')
  const [detail, setDetail] = useState(null)
  const [snapshot, setSnapshot] = useState(null)
  const [editForm, setEditForm] = useState({
    title: '',
    status: 'active',
    summary: '',
    tickersInput: '',
    category: '',
    targetDate: '',
  })
  const [checkpointForm, setCheckpointForm] = useState({ note: '', status_at_check: 'on_track' })

  const isDetail = Boolean(id)

  const loadList = async () => {
    setListLoading(true)
    setListError('')
    try {
      const res = await getTheses(statusFilter)
      setList(res.data || [])
    } catch (e) {
      setListError(e.response?.data?.detail || 'Failed to load thesis list')
      setList([])
    } finally {
      setListLoading(false)
    }
  }

  const loadDetail = async (thesisId) => {
    setDetailLoading(true)
    setDetailError('')
    try {
      const [detailRes, snapshotRes] = await Promise.all([
        getThesis(thesisId),
        getThesisSnapshot(thesisId),
      ])
      setDetail(detailRes.data)
      setSnapshot(snapshotRes.data)
      setEditForm({
        title: detailRes.data.title || '',
        status: detailRes.data.status || 'active',
        summary: detailRes.data.summary || '',
        tickersInput: toTickerInput(detailRes.data.tickers),
        category: detailRes.data.category || '',
        targetDate: detailRes.data.target_date ? detailRes.data.target_date.slice(0, 10) : '',
      })
    } catch (e) {
      setDetailError(e.response?.data?.detail || 'Failed to load thesis detail')
      setDetail(null)
      setSnapshot(null)
    } finally {
      setDetailLoading(false)
    }
  }

  useEffect(() => {
    if (!isDetail) loadList()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isDetail, statusFilter])

  useEffect(() => {
    if (id) loadDetail(id)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id])

  const totalSnapshotChange = useMemo(() => {
    const rows = snapshot?.tickers || []
    if (!rows.length) return null
    const baseline = rows.reduce((sum, row) => sum + (row.baseline_price || 0), 0)
    const current = rows.reduce((sum, row) => sum + (row.current_price || 0), 0)
    if (!baseline) return null
    return ((current - baseline) / baseline) * 100
  }, [snapshot])

  const submitCreate = async (e) => {
    e.preventDefault()
    const tickers = normalizeTickerInput(createForm.tickersInput)
    try {
      const res = await createThesis({
        title: createForm.title.trim(),
        summary: createForm.summary.trim() || null,
        tickers,
        category: createForm.category || null,
        target_date: createForm.targetDate || null,
      })
      setShowCreate(false)
      setCreateForm({ title: '', summary: '', tickersInput: '', category: 'macro', targetDate: '' })
      navigate(`/thesis/${res.data.id}`)
    } catch (e2) {
      alert(e2.response?.data?.detail || 'Failed to create thesis')
    }
  }

  const submitUpdate = async () => {
    if (!id) return
    try {
      await updateThesis(id, {
        title: editForm.title.trim(),
        status: editForm.status,
        summary: editForm.summary.trim() || null,
        tickers: normalizeTickerInput(editForm.tickersInput),
        category: editForm.category || null,
        target_date: editForm.targetDate || null,
      })
      await loadDetail(id)
    } catch (e) {
      alert(e.response?.data?.detail || 'Failed to update thesis')
    }
  }

  const submitCheckpoint = async (e) => {
    e.preventDefault()
    if (!id) return
    try {
      await addThesisCheckpoint(id, {
        note: checkpointForm.note.trim(),
        status_at_check: checkpointForm.status_at_check || null,
      })
      setCheckpointForm({ note: '', status_at_check: 'on_track' })
      await loadDetail(id)
    } catch (e2) {
      alert(e2.response?.data?.detail || 'Failed to add checkpoint')
    }
  }

  const removeThesis = async (targetId, title) => {
    if (!confirm(`Delete thesis "${title}"?`)) return
    try {
      await deleteThesis(targetId)
      if (id && String(id) === String(targetId)) {
        navigate('/thesis')
      } else {
        loadList()
      }
    } catch (e) {
      alert(e.response?.data?.detail || 'Failed to delete thesis')
    }
  }

  if (!isDetail) {
    return (
      <div className="p-6 space-y-5">
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-semibold text-slate-100">Investment Thesis</h1>
          <div className="flex gap-2">
            <button onClick={loadList} className="btn-ghost"><RefreshCw size={15} /></button>
            <button onClick={() => setShowCreate((v) => !v)} className="btn-primary"><Plus size={15} /> New Thesis</button>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <label className="text-xs text-slate-500">Status</label>
          <select className="select w-44" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            <option value="">All</option>
            {STATUSES.map((status) => <option key={status} value={status}>{status}</option>)}
          </select>
        </div>

        {showCreate && (
          <div className="card">
            <p className="card-title">Create Thesis</p>
            <form className="space-y-3" onSubmit={submitCreate}>
              <input
                className="input"
                placeholder="Title"
                value={createForm.title}
                onChange={(e) => setCreateForm((f) => ({ ...f, title: e.target.value }))}
                required
              />
              <textarea
                className="input"
                placeholder="Summary"
                rows={3}
                value={createForm.summary}
                onChange={(e) => setCreateForm((f) => ({ ...f, summary: e.target.value }))}
              />
              <input
                className="input uppercase"
                placeholder="Tickers, comma separated (e.g. AEVA,LAZR,INVZ,OUST)"
                value={createForm.tickersInput}
                onChange={(e) => setCreateForm((f) => ({ ...f, tickersInput: e.target.value }))}
                required
              />
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <input
                  className="input"
                  placeholder="Category (macro/growth/value/sector)"
                  value={createForm.category}
                  onChange={(e) => setCreateForm((f) => ({ ...f, category: e.target.value }))}
                />
                <input
                  className="input"
                  type="date"
                  value={createForm.targetDate}
                  onChange={(e) => setCreateForm((f) => ({ ...f, targetDate: e.target.value }))}
                />
              </div>
              <button type="submit" className="btn-primary">Create</button>
            </form>
          </div>
        )}

        {listError && <p className="text-sm text-red-400">{listError}</p>}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {listLoading && <p className="text-sm text-slate-500">Loading theses…</p>}
          {!listLoading && list.length === 0 && (
            <p className="text-sm text-slate-500">No thesis yet.</p>
          )}

          {list.map((item) => (
            <div key={item.id} className="card">
              <div className="flex items-start justify-between gap-3 mb-2">
                <div>
                  <p className="text-base font-semibold text-slate-100">{item.title}</p>
                  <p className="text-xs text-slate-500">Created: {fmtDate(item.created_at)}</p>
                </div>
                <StatusBadge status={item.status} />
              </div>
              <p className="text-sm text-slate-400 line-clamp-3 mb-3">{item.summary || 'No summary'}</p>
              <div className="flex flex-wrap gap-2 mb-3">
                {(item.tickers || []).map((row) => (
                  <span key={row.ticker} className="badge bg-slate-800 text-slate-300">{row.ticker}</span>
                ))}
              </div>
              <div className="flex gap-2">
                <button onClick={() => navigate(`/thesis/${item.id}`)} className="btn-primary !py-1.5">View</button>
                <button onClick={() => removeThesis(item.id, item.title)} className="btn-ghost !py-1.5 text-red-300"><Trash2 size={14} /></button>
              </div>
            </div>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <button className="btn-ghost" onClick={() => navigate('/thesis')}>
          <ArrowLeft size={15} /> Back
        </button>
        {detail && (
          <button className="btn-ghost text-red-300" onClick={() => removeThesis(detail.id, detail.title)}>
            <Trash2 size={15} /> Delete
          </button>
        )}
      </div>

      {detailLoading && <p className="text-sm text-slate-500">Loading thesis detail…</p>}
      {detailError && <p className="text-sm text-red-400">{detailError}</p>}

      {detail && (
        <>
          <div className="card space-y-3">
            <div className="flex items-start justify-between gap-4">
              <h1 className="text-xl font-semibold text-slate-100">{detail.title}</h1>
              <StatusBadge status={detail.status} />
            </div>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
              <input
                className="input"
                value={editForm.title}
                onChange={(e) => setEditForm((f) => ({ ...f, title: e.target.value }))}
                placeholder="Title"
              />
              <select
                className="select"
                value={editForm.status}
                onChange={(e) => setEditForm((f) => ({ ...f, status: e.target.value }))}
              >
                {STATUSES.map((status) => <option key={status} value={status}>{status}</option>)}
              </select>
              <input
                className="input uppercase"
                value={editForm.tickersInput}
                onChange={(e) => setEditForm((f) => ({ ...f, tickersInput: e.target.value }))}
                placeholder="Tickers"
              />
              <input
                className="input"
                type="date"
                value={editForm.targetDate}
                onChange={(e) => setEditForm((f) => ({ ...f, targetDate: e.target.value }))}
              />
            </div>
            <textarea
              className="input"
              rows={4}
              value={editForm.summary}
              onChange={(e) => setEditForm((f) => ({ ...f, summary: e.target.value }))}
              placeholder="Summary"
            />
            <div className="flex items-center gap-3 text-xs text-slate-500">
              <span>Created: {fmtDate(detail.created_at)}</span>
              <span>Updated: {fmtDate(detail.updated_at)}</span>
            </div>
            <button className="btn-primary" onClick={submitUpdate}><Save size={15} /> Save</button>
          </div>

          <div className="card">
            <p className="card-title">Snapshot</p>
            {snapshot?.tickers?.length ? (
              <>
                {totalSnapshotChange != null && (
                  <p className={`text-sm mb-2 ${gainColor(totalSnapshotChange)}`}>
                    Basket change since baseline: {fmtPct(totalSnapshotChange, 2)}
                  </p>
                )}
                <div className="overflow-x-auto">
                  <table className="w-full text-xs min-w-[680px]">
                    <thead>
                      <tr className="border-b border-slate-700">
                        <th className="th">Ticker</th>
                        <th className="th text-right">Baseline Close</th>
                        <th className="th text-right">Current</th>
                        <th className="th text-right">Change</th>
                        <th className="th text-right">Change %</th>
                        <th className="th text-right">Day %</th>
                      </tr>
                    </thead>
                    <tbody>
                      {snapshot.tickers.map((row) => (
                        <tr key={row.ticker} className="table-row">
                          <td className="td text-slate-200 font-mono">{row.ticker}</td>
                          <td className="td text-right text-slate-400">{fmtCurrency(row.baseline_price)}</td>
                          <td className="td text-right">{fmtCurrency(row.current_price)}</td>
                          <td className={`td text-right ${gainColor(row.change_abs)}`}>{fmtCurrency(row.change_abs)}</td>
                          <td className={`td text-right ${gainColor(row.change_pct)}`}>{fmtPct(row.change_pct, 2)}</td>
                          <td className={`td text-right ${gainColor(row.day_change_pct)}`}>{fmtPct(row.day_change_pct, 2)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            ) : (
              <p className="text-sm text-slate-500">No snapshot data.</p>
            )}
          </div>

          <div className="card">
            <p className="card-title">Checkpoints</p>
            <form className="space-y-3 mb-4" onSubmit={submitCheckpoint}>
              <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
                <textarea
                  className="input md:col-span-3"
                  rows={2}
                  value={checkpointForm.note}
                  onChange={(e) => setCheckpointForm((f) => ({ ...f, note: e.target.value }))}
                  placeholder="Checkpoint note"
                  required
                />
                <div className="space-y-2">
                  <select
                    className="select"
                    value={checkpointForm.status_at_check}
                    onChange={(e) => setCheckpointForm((f) => ({ ...f, status_at_check: e.target.value }))}
                  >
                    {CHECKPOINT_STATUSES.map((status) => <option key={status} value={status}>{status}</option>)}
                  </select>
                  <button type="submit" className="btn-primary w-full"><Plus size={14} /> Add</button>
                </div>
              </div>
            </form>

            <div className="space-y-3">
              {(detail.checkpoints || []).length === 0 && (
                <p className="text-sm text-slate-500">No checkpoints yet.</p>
              )}
              {(detail.checkpoints || []).map((cp) => (
                <div key={cp.id} className="border border-slate-700 rounded-lg p-3">
                  <div className="flex items-center justify-between gap-2 mb-1">
                    <span className={`badge border ${STATUS_STYLE[cp.status_at_check] || STATUS_STYLE.active}`}>
                      {cp.status_at_check || 'unlabeled'}
                    </span>
                    <span className="text-xs text-slate-500">{fmtDate(cp.created_at)}</span>
                  </div>
                  <p className="text-sm text-slate-300 whitespace-pre-wrap">{cp.note}</p>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
