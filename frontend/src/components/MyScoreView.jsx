import { useState, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'

function scoreColor(score) {
  if (score == null) return 'text-slate-400'
  if (score >= 80) return 'text-green-600'
  if (score >= 60) return 'text-amber-600'
  return 'text-red-600'
}

function gateLabel(score) {
  if (score == null) return { label: 'No data', cls: 'text-slate-500 border-slate-300 bg-slate-50' }
  if (score >= 80) return { label: 'Pass', cls: 'text-green-700 border-green-300 bg-green-50' }
  if (score >= 60) return { label: 'Warning', cls: 'text-amber-700 border-amber-300 bg-amber-50' }
  return { label: 'Fail', cls: 'text-red-700 border-red-300 bg-red-50' }
}

function ScoreBar({ score }) {
  const s = Math.min(100, Math.max(0, Number(score) || 0))
  const color = s >= 80 ? 'bg-green-500' : s >= 60 ? 'bg-amber-500' : 'bg-red-500'
  return (
    <div className="w-full bg-slate-200 h-2 rounded-full">
      <div className={`${color} h-2 rounded-full transition-all`} style={{ width: `${s}%` }} />
    </div>
  )
}

function MiniBar({ score }) {
  const s = Math.min(100, Math.max(0, Number(score) || 0))
  const color = s >= 80 ? 'bg-green-500' : s >= 60 ? 'bg-amber-500' : 'bg-red-500'
  return (
    <div className="w-20 bg-slate-200 h-2 rounded-full">
      <div className={`${color} h-2 rounded-full`} style={{ width: `${s}%` }} />
    </div>
  )
}

export default function MyScoreView() {
  const { user, authFetch } = useAuth()
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    authFetch('/api/team/me/history')
      .then(r => r.json())
      .then(data => setHistory(Array.isArray(data) ? data : []))
      .catch(() => setHistory([]))
      .finally(() => setLoading(false))
  }, [])

  const latest = history[0] ?? null
  const { label: gLabel, cls: gCls } = gateLabel(latest?.score)

  return (
    <div className="p-6 max-w-3xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-900">My Compliance Score</h1>
        <p className="text-slate-500 text-sm mt-1">{user?.name} · {user?.email}</p>
      </div>

      {/* Latest score card */}
      <div className="bg-white border border-slate-200 p-5 mb-6 rounded-sm shadow-sm">
        <p className="text-xs text-slate-500 uppercase tracking-wide font-semibold mb-3">Latest Analysis</p>
        {latest == null ? (
          <p className="text-slate-500 text-sm">No analyses yet — run one from the Analysis tab to see your score.</p>
        ) : (
          <>
            <div className="flex items-end gap-4 mb-3">
              <span className={`text-6xl font-black tabular-nums ${scoreColor(latest.score)}`}>
                {Math.round(latest.score)}
              </span>
              <div className="mb-2 space-y-1">
                <span className={`text-sm px-2.5 py-1 border font-semibold rounded-sm ${gCls}`}>{gLabel}</span>
                <p className="text-xs text-slate-400">out of 100 · threshold 80</p>
              </div>
            </div>
            <ScoreBar score={latest.score} />
            <div className="mt-3 flex flex-wrap gap-4 text-xs text-slate-500">
              <span>{(latest.repo_url || '').replace('https://github.com/', '').replace('https://', '')}</span>
              <span>{latest.timestamp}</span>
              {latest.issue_count > 0 && <span className="text-slate-500">{latest.issue_count} issues</span>}
              {latest.critical_count > 0 && <span className="text-red-600 font-semibold">{latest.critical_count} critical</span>}
            </div>
            {latest.summary && (
              <p className="mt-3 text-sm text-slate-600 border-t border-slate-100 pt-3 leading-relaxed">
                {latest.summary}
              </p>
            )}
          </>
        )}
      </div>

      {/* History */}
      <div>
        <p className="text-xs text-slate-500 uppercase tracking-wide font-semibold mb-3">
          Analysis History ({history.length})
        </p>
        {loading && <p className="text-slate-400 text-sm">Loading...</p>}
        {!loading && history.length === 0 && (
          <div className="border border-dashed border-slate-300 py-10 text-center text-slate-400 text-sm rounded-sm bg-white">
            No analyses recorded yet.
          </div>
        )}
        {!loading && history.length > 0 && (
          <div className="space-y-2">
            {history.map((h, i) => (
              <div key={i} className="bg-white border border-slate-200 p-4 hover:border-slate-300 transition-colors rounded-sm shadow-sm">
                <div className="flex items-center justify-between gap-4 flex-wrap">
                  <div>
                    <p className="text-sm text-slate-800 font-medium">
                      {(h.repo_url || '').replace('https://github.com/', '').replace('https://', '')}
                    </p>
                    <p className="text-xs text-slate-400 mt-0.5">{h.timestamp}</p>
                  </div>
                  <div className="flex items-center gap-3 shrink-0">
                    <span className={`text-xl font-bold tabular-nums ${scoreColor(h.score)}`}>
                      {Math.round(h.score)}
                    </span>
                    <MiniBar score={h.score} />
                    {h.issue_count > 0 && (
                      <span className="text-xs text-slate-600 bg-slate-100 border border-slate-200 px-2 py-0.5 rounded-sm">
                        {h.issue_count} issues
                      </span>
                    )}
                    {h.critical_count > 0 && (
                      <span className="text-xs text-red-700 bg-red-50 border border-red-200 px-2 py-0.5 rounded-sm font-semibold">
                        {h.critical_count} critical
                      </span>
                    )}
                  </div>
                </div>
                {h.summary && (
                  <p className="text-xs text-slate-500 mt-2 border-t border-slate-100 pt-2 leading-relaxed">
                    {h.summary}
                  </p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
