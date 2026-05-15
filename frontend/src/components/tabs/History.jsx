import { useState, useEffect } from 'react'
import { useAuth } from '../../contexts/AuthContext'

function ScoreBar({ score }) {
  const s = Math.min(100, Math.max(0, Number(score) || 0))
  const color = s >= 80 ? 'bg-green-500' : s >= 60 ? 'bg-amber-500' : 'bg-red-500'
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 bg-zinc-700 h-1.5 rounded-full">
        <div className={`${color} h-1.5 rounded-full transition-all`} style={{ width: `${s}%` }} />
      </div>
      <span className="text-xs text-zinc-500 w-8 text-right tabular-nums">{s.toFixed(0)}</span>
    </div>
  )
}

function DownloadButton({ entry, repoUrl }) {
  const { authFetch } = useAuth()
  const [loading, setLoading] = useState(false)

  const handleDownload = async () => {
    if (!entry.id) return
    setLoading(true)
    try {
      const res = await authFetch(`/api/history/report/${entry.id}`)
      if (!res.ok) throw new Error('Failed')
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `driftx_${(entry.timestamp || 'report').replace(/[: ]/g, '_')}.pdf`
      a.click()
      URL.revokeObjectURL(url)
    } catch (_) {}
    setLoading(false)
  }

  return (
    <button
      onClick={handleDownload}
      disabled={loading}
      title="Download PDF report for this analysis"
      className="shrink-0 flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium border border-zinc-700 bg-zinc-800 text-zinc-400 hover:bg-neon-500/10 hover:border-neon-500 hover:text-neon-500 disabled:opacity-40 disabled:cursor-not-allowed transition-colors rounded-sm"
    >
      {loading ? (
        <span className="animate-spin inline-block">⟳</span>
      ) : (
        <span>⬇</span>
      )}
      {loading ? 'Generating...' : 'PDF'}
    </button>
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
  const totalCommits = meta.total_commits ?? historyResults?.total_commits_analyzed ?? 0
  const commitsWithDeletions = historyResults?.commits_with_deletions ?? meta.commits_with_deletions ?? 0
  const criticalIssues = historyResults?.critical_issues_found ?? 0
  const deploymentRisk = historyResults?.deployment_risk ?? null

  const riskCls = { High: 'text-red-400', Medium: 'text-amber-400', Low: 'text-green-400' }

  return (
    <div className="space-y-6">
      {/* Git metadata stats */}
      {historyResults && !historyResults.error && (
        <div>
          <p className="text-sm font-semibold text-zinc-300 mb-3">Git Metadata &amp; Risk</p>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {[
              { label: 'Commits Analyzed', value: totalCommits },
              { label: 'Commits w/ Deletions', value: commitsWithDeletions },
              { label: 'Critical Issues', value: criticalIssues },
            ].map(s => (
              <div key={s.label} className="bg-zinc-800 border border-zinc-700 p-4 rounded-sm shadow-sm">
                <p className="text-xs text-zinc-500 font-medium">{s.label}</p>
                <p className="text-xl font-bold text-zinc-100 mt-1">{s.value}</p>
              </div>
            ))}
            <div className="bg-zinc-800 border border-zinc-700 p-4 rounded-sm shadow-sm">
              <p className="text-xs text-zinc-500 font-medium mb-1">Deployment Risk</p>
              <p className={`font-semibold text-sm ${riskCls[deploymentRisk] || 'text-zinc-500'}`}>
                {deploymentRisk || 'Unknown'}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Past analyses */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <p className="text-sm font-semibold text-zinc-300">Past Analyses</p>
          {history.length > 0 && (
            <button
              onClick={clearHistory}
              disabled={clearing}
              className="text-xs text-zinc-500 hover:text-red-400 transition-colors disabled:opacity-40"
            >
              {clearing ? 'Clearing...' : 'Clear History'}
            </button>
          )}
        </div>

        {loading && (
          <p className="text-sm text-zinc-500 text-center py-8">Loading history...</p>
        )}

        {!loading && history.length === 0 && (
          <div className="text-center py-8 text-zinc-500 border border-dashed border-zinc-700 bg-zinc-800/50 rounded-sm">
            No past analyses for this repository.
          </div>
        )}

        {!loading && history.length > 0 && (
          <div className="space-y-2">
            {history.map((entry, i) => (
              <div key={i} className="bg-zinc-800 border border-zinc-700 p-4 rounded-sm shadow-sm hover:border-zinc-600 transition-colors">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap mb-1.5">
                      <span className="text-xs text-zinc-500 tabular-nums">{entry.timestamp}</span>
                      <span className="text-xs bg-zinc-700/60 border border-zinc-700 text-zinc-400 px-2 py-0.5 rounded-sm">{entry.type}</span>
                      {i === 0 && (
                        <span className="text-xs bg-neon-500/10 text-neon-500 px-2 py-0.5 rounded-sm border border-neon-500/30 font-semibold">
                          Latest
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-zinc-400 leading-relaxed">{entry.summary}</p>
                    <div className="mt-2 max-w-52">
                      <ScoreBar score={entry.score} />
                    </div>
                  </div>

                  {/* Download button */}
                  <DownloadButton entry={entry} repoUrl={repoUrl} />
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
