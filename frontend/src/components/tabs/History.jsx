import { useState, useEffect } from 'react'
import { useAuth } from '../../contexts/AuthContext'

function RiskBadge({ risk }) {
  const styles = { High: 'text-red-400', Medium: 'text-amber-400', Low: 'text-green-400' }
  const icons = { High: '🔴', Medium: '🟡', Low: '🟢' }
  return (
    <span className={`font-medium ${styles[risk] || 'text-slate-400'}`}>
      {icons[risk] || '⚪'} {risk || 'Unknown'}
    </span>
  )
}

function ScoreBar({ score }) {
  const s = Math.min(100, Math.max(0, Number(score) || 0))
  const color = s >= 80 ? 'bg-green-500' : s >= 60 ? 'bg-amber-500' : 'bg-red-500'
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 bg-navy-800  h-1.5">
        <div className={`${color} h-1.5  transition-all`} style={{ width: `${s}%` }} />
      </div>
      <span className="text-xs text-slate-400 w-10 text-right tabular-nums">{s.toFixed(1)}</span>
    </div>
  )
}

export default function History({ repoUrl, historyResults }) {
  const { authFetch } = useAuth()
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(false)
  const [clearing, setClearing] = useState(false)

  const fetchHistory = async () => {
    if (!repoUrl) return
    setLoading(true)
    try {
      const res = await authFetch(`/api/history?repo_url=${encodeURIComponent(repoUrl)}`)
      const data = await res.json()
      setHistory(Array.isArray(data) ? data : [])
    } catch (_) {}
    setLoading(false)
  }

  useEffect(() => { fetchHistory() }, [repoUrl])

  const clearHistory = async () => {
    setClearing(true)
    try {
      await authFetch(`/api/history?repo_url=${encodeURIComponent(repoUrl)}`, { method: 'DELETE' })
      setHistory([])
    } catch (_) {}
    setClearing(false)
  }

  const meta = historyResults?.analysis_metadata ?? {}
  const totalCommits = historyResults?.total_commits_analyzed ?? meta.total_commits ?? 0
  const commitsWithDeletions = historyResults?.commits_with_deletions ?? 0
  const criticalIssues = historyResults?.critical_issues_found ?? 0
  const deploymentRisk = historyResults?.deployment_risk ?? null

  return (
    <div className="space-y-6">
      {historyResults && !historyResults.error && (
        <div>
          <p className="text-sm font-semibold text-slate-300 mb-3">📊 Git Metadata & Risk</p>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <StatCard label="Commits Analyzed" value={totalCommits} />
            <StatCard label="Commits w/ Deletions" value={commitsWithDeletions} />
            <StatCard label="Critical Issues" value={criticalIssues} />
            <div className="bg-navy-800/60 border border-navy-700  p-4">
              <p className="text-xs text-slate-500 mb-1 font-medium">Deployment Risk</p>
              <RiskBadge risk={deploymentRisk} />
            </div>
          </div>
        </div>
      )}

      <div>
        <div className="flex items-center justify-between mb-3">
          <p className="text-sm font-semibold text-slate-300">🕰️ Past Analyses</p>
          {history.length > 0 && (
            <button
              onClick={clearHistory}
              disabled={clearing}
              className="text-xs text-slate-500 hover:text-red-400 transition-colors disabled:opacity-40"
            >
              {clearing ? 'Clearing…' : '🗑️ Clear History'}
            </button>
          )}
        </div>

        {loading && (
          <p className="text-sm text-slate-600 text-center py-8">Loading history…</p>
        )}

        {!loading && history.length === 0 && (
          <div className="text-center py-8 text-slate-600 border border-dashed border-navy-700 ">
            No past analyses for this repository.
          </div>
        )}

        {!loading && history.length > 0 && (
          <div className="space-y-3">
            {history.map((entry, i) => (
              <div key={i} className="bg-navy-900 border border-navy-700  p-4">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-xs text-slate-500">{entry.timestamp}</span>
                      <span className="text-xs bg-navy-800 border border-navy-700 text-slate-400 px-2 py-0.5 ">{entry.type}</span>
                      {i === 0 && (
                        <span className="text-xs bg-orange-900/40 text-orange-400 px-2 py-0.5  border border-orange-800/60">
                          Latest
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-slate-400 mt-1.5">{entry.summary}</p>
                    <div className="mt-2 max-w-48">
                      <ScoreBar score={entry.score} />
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function StatCard({ label, value }) {
  return (
    <div className="bg-navy-800/60 border border-navy-700  p-4">
      <p className="text-xs text-slate-500 font-medium">{label}</p>
      <p className="text-xl font-bold text-white mt-1">{value}</p>
    </div>
  )
}
