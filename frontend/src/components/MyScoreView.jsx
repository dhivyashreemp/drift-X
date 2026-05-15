import { useState, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'

function scoreColor(score) {
  if (score == null) return 'text-zinc-500'
  if (score >= 80) return 'text-green-400'
  if (score >= 60) return 'text-amber-400'
  return 'text-red-400'
}

function gateLabel(score) {
  if (score == null) return { label: 'No data', cls: 'text-zinc-500 border-zinc-600 bg-zinc-800' }
  if (score >= 80) return { label: 'Pass', cls: 'text-green-400 border-green-700/50 bg-green-950/40' }
  if (score >= 60) return { label: 'Warning', cls: 'text-amber-400 border-amber-700/50 bg-amber-950/40' }
  return { label: 'Fail', cls: 'text-red-400 border-red-700/50 bg-red-950/40' }
}

function ScoreBar({ score }) {
  const s = Math.min(100, Math.max(0, Number(score) || 0))
  const color = s >= 80 ? 'bg-green-500' : s >= 60 ? 'bg-amber-500' : 'bg-red-500'
  return (
    <div className="w-full bg-zinc-700 h-2 rounded-full">
      <div className={`${color} h-2 rounded-full transition-all`} style={{ width: `${s}%` }} />
    </div>
  )
}

function MiniBar({ score }) {
  const s = Math.min(100, Math.max(0, Number(score) || 0))
  const color = s >= 80 ? 'bg-green-500' : s >= 60 ? 'bg-amber-500' : 'bg-red-500'
  return (
    <div className="w-20 bg-zinc-700 h-2 rounded-full">
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
        <h1 className="text-2xl font-bold text-zinc-100">My Compliance Score</h1>
        <p className="text-zinc-500 text-sm mt-1">{user?.name} · {user?.email}</p>
      </div>

      {/* Latest score card */}
      <div className="bg-zinc-800 border border-zinc-700 p-5 mb-6 rounded-sm shadow-sm">
        <p className="text-xs text-zinc-500 uppercase tracking-wide font-semibold mb-3">Latest Analysis</p>
        {latest == null ? (
          <p className="text-zinc-400 text-sm">No analyses yet — run one from the Analysis tab to see your score.</p>
        ) : (
          <>
            <div className="flex items-end gap-4 mb-3">
              <span className={`text-6xl font-black tabular-nums ${scoreColor(latest.score)}`}>
                {Math.round(latest.score)}
              </span>
              <div className="mb-2 space-y-1">
                <span className={`text-sm px-2.5 py-1 border font-semibold rounded-sm ${gCls}`}>{gLabel}</span>
                <p className="text-xs text-zinc-500">out of 100 · threshold 80</p>
              </div>
            </div>
            <ScoreBar score={latest.score} />
            <div className="mt-3 flex flex-wrap gap-4 text-xs text-zinc-500">
              <span>{(latest.repo_url || '').replace('https://github.com/', '').replace('https://', '')}</span>
              <span>{latest.timestamp}</span>
              {latest.issue_count > 0 && <span>{latest.issue_count} issues</span>}
              {latest.critical_count > 0 && <span className="text-red-400 font-semibold">{latest.critical_count} critical</span>}
            </div>
            {latest.summary && (
              <p className="mt-3 text-sm text-zinc-400 border-t border-zinc-700 pt-3 leading-relaxed">
                {latest.summary}
              </p>
            )}
          </>
        )}
      </div>

      {/* History */}
      <div>
        <p className="text-xs text-zinc-500 uppercase tracking-wide font-semibold mb-3">
          Analysis History ({history.length})
        </p>
        {loading && <p className="text-zinc-400 text-sm">Loading...</p>}
        {!loading && history.length === 0 && (
          <div className="border border-dashed border-zinc-700 py-10 text-center text-zinc-500 text-sm rounded-sm bg-zinc-900">
            No analyses recorded yet.
          </div>
        )}
        {!loading && history.length > 0 && (
          <div className="space-y-2">
            {history.map((h, i) => (
              <div key={i} className="bg-zinc-800 border border-zinc-700 p-4 hover:border-zinc-600 transition-colors rounded-sm shadow-sm">
                <div className="flex items-center justify-between gap-4 flex-wrap">
                  <div>
                    <p className="text-sm text-zinc-200 font-medium">
                      {(h.repo_url || '').replace('https://github.com/', '').replace('https://', '')}
                    </p>
                    <p className="text-xs text-zinc-500 mt-0.5">{h.timestamp}</p>
                  </div>
                  <div className="flex items-center gap-3 shrink-0">
                    <span className={`text-xl font-bold tabular-nums ${scoreColor(h.score)}`}>
                      {Math.round(h.score)}
                    </span>
                    <MiniBar score={h.score} />
                    {h.issue_count > 0 && (
                      <span className="text-xs text-zinc-400 bg-zinc-700 border border-zinc-600 px-2 py-0.5 rounded-sm">
                        {h.issue_count} issues
                      </span>
                    )}
                    {h.critical_count > 0 && (
                      <span className="text-xs text-red-400 bg-red-950/40 border border-red-700/50 px-2 py-0.5 rounded-sm font-semibold">
                        {h.critical_count} critical
                      </span>
                    )}
                  </div>
                </div>
                {h.summary && (
                  <p className="text-xs text-zinc-500 mt-2 border-t border-zinc-700 pt-2 leading-relaxed">
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
