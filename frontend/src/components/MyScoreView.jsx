import { useState, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'

function scoreColor(score) {
  if (score == null) return 'text-slate-600'
  if (score >= 80) return 'text-green-400'
  if (score >= 60) return 'text-amber-400'
  return 'text-red-400'
}

function gateLabel(score) {
  if (score == null) return { label: 'No data', cls: 'text-slate-500 border-navy-700' }
  if (score >= 80) return { label: '✓ Pass', cls: 'text-green-400 border-green-900 bg-green-950/30' }
  if (score >= 60) return { label: '⚠ Warning', cls: 'text-amber-400 border-amber-900 bg-amber-950/30' }
  return { label: '✗ Fail', cls: 'text-red-400 border-red-900 bg-red-950/30' }
}

function ScoreBar({ score }) {
  const s = Math.min(100, Math.max(0, Number(score) || 0))
  const color = s >= 80 ? 'bg-green-500' : s >= 60 ? 'bg-amber-500' : 'bg-red-500'
  return (
    <div className="w-full bg-navy-800 h-2">
      <div className={`${color} h-2 transition-all`} style={{ width: `${s}%` }} />
    </div>
  )
}

function MiniBar({ score }) {
  const s = Math.min(100, Math.max(0, Number(score) || 0))
  const color = s >= 80 ? 'bg-green-500' : s >= 60 ? 'bg-amber-500' : 'bg-red-500'
  return (
    <div className="w-20 bg-navy-800 h-2">
      <div className={`${color} h-2`} style={{ width: `${s}%` }} />
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
        <h1 className="text-2xl font-bold text-white">My Compliance Score</h1>
        <p className="text-slate-400 text-sm mt-1">{user?.name} · {user?.email}</p>
      </div>

      {/* Latest score card */}
      <div className="bg-navy-900 border border-navy-800 p-5 mb-6">
        <p className="text-xs text-slate-500 uppercase tracking-wide font-medium mb-3">Latest Analysis</p>
        {latest == null ? (
          <p className="text-slate-500 text-sm">No analyses yet — run one from the Analysis tab to see your score.</p>
        ) : (
          <>
            <div className="flex items-end gap-4 mb-3">
              <span className={`text-6xl font-black tabular-nums ${scoreColor(latest.score)}`}>
                {Math.round(latest.score)}
              </span>
              <div className="mb-2 space-y-1">
                <span className={`text-sm px-2 py-1 border ${gCls}`}>{gLabel}</span>
                <p className="text-xs text-slate-500">out of 100 · threshold 90</p>
              </div>
            </div>
            <ScoreBar score={latest.score} />
            <div className="mt-3 flex flex-wrap gap-4 text-xs text-slate-500">
              <span>{(latest.repo_url || '').replace('https://github.com/', '').replace('https://', '')}</span>
              <span>{latest.timestamp}</span>
              {latest.issue_count > 0 && <span className="text-slate-400">{latest.issue_count} issues</span>}
              {latest.critical_count > 0 && <span className="text-red-400 font-semibold">{latest.critical_count} critical</span>}
            </div>
            {latest.summary && (
              <p className="mt-3 text-xs text-slate-400 border-t border-navy-700 pt-3 leading-relaxed">
                {latest.summary}
              </p>
            )}
          </>
        )}
      </div>

      {/* History */}
      <div>
        <p className="text-xs text-slate-500 uppercase tracking-wide font-medium mb-3">
          Analysis History ({history.length})
        </p>
        {loading && <p className="text-slate-600 text-sm">Loading…</p>}
        {!loading && history.length === 0 && (
          <div className="border border-dashed border-navy-800 py-10 text-center text-slate-600 text-sm">
            No analyses recorded yet.
          </div>
        )}
        {!loading && history.length > 0 && (
          <div className="space-y-2">
            {history.map((h, i) => (
              <div key={i} className="bg-navy-900 border border-navy-800 p-4 hover:border-navy-600 transition-colors">
                <div className="flex items-center justify-between gap-4 flex-wrap">
                  <div>
                    <p className="text-sm text-slate-300 font-medium">
                      {(h.repo_url || '').replace('https://github.com/', '').replace('https://', '')}
                    </p>
                    <p className="text-xs text-slate-500 mt-0.5">{h.timestamp}</p>
                  </div>
                  <div className="flex items-center gap-3 shrink-0">
                    <span className={`text-xl font-bold tabular-nums ${scoreColor(h.score)}`}>
                      {Math.round(h.score)}
                    </span>
                    <MiniBar score={h.score} />
                    {h.issue_count > 0 && (
                      <span className="text-xs text-slate-500 bg-navy-800 border border-navy-700 px-2 py-0.5">
                        {h.issue_count} issues
                      </span>
                    )}
                    {h.critical_count > 0 && (
                      <span className="text-xs text-red-400 bg-red-950/30 border border-red-900 px-2 py-0.5">
                        {h.critical_count} critical
                      </span>
                    )}
                  </div>
                </div>
                {h.summary && (
                  <p className="text-xs text-slate-400 mt-2 border-t border-navy-700/60 pt-2 leading-relaxed">
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
