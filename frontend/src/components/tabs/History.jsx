import { useState, useEffect } from 'react'
import { useAuth } from '../../contexts/AuthContext'
import QualityReport from './QualityReport'
import Issues from './Issues'
import FeatureEvolution from './FeatureEvolution'

function ScoreBar({ score }) {
  const s = Math.min(100, Math.max(0, Number(score) || 0))
  const color = s >= 80 ? 'bg-green-500' : s >= 60 ? 'bg-amber-500' : 'bg-red-500'
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 bg-slate-200 h-1.5 rounded-full">
        <div className={`${color} h-1.5 rounded-full transition-all`} style={{ width: `${s}%` }} />
      </div>
      <span className="text-xs text-slate-500 w-8 text-right tabular-nums">{s.toFixed(0)}</span>
    </div>
  )
}

function DownloadButton({ entry }) {
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
      disabled={loading || !entry.id}
      title="Download full PDF report"
      className="shrink-0 flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold border border-slate-300 bg-white text-slate-600 hover:bg-orange-50 hover:border-orange-400 hover:text-orange-600 disabled:opacity-40 disabled:cursor-not-allowed transition-colors rounded-sm"
    >
      {loading ? <span className="animate-spin inline-block">⟳</span> : <span>⬇</span>}
      {loading ? 'Generating...' : 'PDF'}
    </button>
  )
}

const REPORT_TABS = [
  { id: 'quality', label: 'Quality Report' },
  { id: 'issues', label: 'Issues' },
  { id: 'evolution', label: 'Evolution' },
]

function InlineReport({ entryId, onClose }) {
  const { authFetch } = useAuth()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [activeTab, setActiveTab] = useState('quality')

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError('')
    authFetch(`/api/history/entry/${entryId}`)
      .then(r => r.ok ? r.json() : r.json().then(e => { throw new Error(e.detail || 'Failed') }))
      .then(d => { if (!cancelled) { setData(d); setLoading(false) } })
      .catch(e => { if (!cancelled) { setError(e.message); setLoading(false) } })
    return () => { cancelled = true }
  }, [entryId])

  const issueCount = data?.full_results?.issues?.length || 0

  return (
    <div className="mt-3 border border-orange-200 bg-orange-50/30 rounded-sm overflow-hidden">
      {/* Inline header */}
      <div className="flex items-center justify-between px-4 py-2.5 bg-orange-50 border-b border-orange-200">
        <span className="text-xs font-bold text-orange-700 uppercase tracking-wider">Full Analysis Report</span>
        <button
          onClick={onClose}
          className="text-xs text-slate-500 hover:text-red-500 transition-colors font-medium px-2 py-1 rounded hover:bg-red-50"
        >
          ✕ Close
        </button>
      </div>

      {loading && (
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-orange-500 border-b-2" />
          <span className="ml-3 text-sm text-slate-500">Loading full report...</span>
        </div>
      )}

      {error && (
        <div className="p-4 text-sm text-red-600 bg-red-50 border-t border-red-200">
          Failed to load report: {error}
        </div>
      )}

      {data && !loading && (
        <div>
          {/* Tab bar */}
          <div className="flex border-b border-slate-200 bg-white">
            {REPORT_TABS.map(t => (
              <button
                key={t.id}
                onClick={() => setActiveTab(t.id)}
                className={`px-5 py-3 text-sm font-semibold transition-all border-b-2 flex items-center gap-1.5 ${
                  activeTab === t.id
                    ? 'border-orange-500 text-orange-600 bg-orange-50/60'
                    : 'border-transparent text-slate-500 hover:text-slate-800 hover:bg-slate-50'
                }`}
              >
                {t.label}
                {t.id === 'issues' && issueCount > 0 && (
                  <span className="bg-red-100 text-red-700 text-[10px] px-1.5 py-0.5 rounded-full font-bold min-w-[18px] text-center">
                    {issueCount}
                  </span>
                )}
              </button>
            ))}
          </div>

          {/* Tab content */}
          <div className="p-5 bg-white">
            {activeTab === 'quality' && (
              <QualityReport
                results={data.full_results}
                historyResults={data.history_results}
              />
            )}
            {activeTab === 'issues' && (
              <Issues issues={data.full_results?.issues || []} />
            )}
            {activeTab === 'evolution' && (
              <FeatureEvolution historyResults={data.history_results} />
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export default function History({ repoUrl, historyResults }) {
  const { authFetch } = useAuth()
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(false)
  const [clearing, setClearing] = useState(false)
  const [expandedId, setExpandedId] = useState(null)

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
      setExpandedId(null)
    } catch (_) {}
    setClearing(false)
  }

  const toggleExpand = (id) => setExpandedId(prev => prev === id ? null : id)

  const meta = historyResults?.analysis_metadata ?? {}
  const totalCommits = historyResults?.total_commits_analyzed ?? meta.total_commits ?? 0
  const commitsWithDeletions = historyResults?.commits_with_deletions ?? 0
  const criticalIssues = historyResults?.critical_issues_found ?? 0
  const deploymentRisk = historyResults?.deployment_risk ?? null

  const riskCls = { High: 'text-red-600', Medium: 'text-amber-600', Low: 'text-green-600' }

  return (
    <div className="space-y-6">
      {/* Git metadata stats */}
      {historyResults && !historyResults.error && (
        <div>
          <p className="text-sm font-semibold text-slate-700 mb-3">Git Metadata &amp; Risk</p>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {[
              { label: 'Commits Analyzed', value: totalCommits },
              { label: 'Commits w/ Deletions', value: commitsWithDeletions },
              { label: 'Critical Issues', value: criticalIssues },
            ].map(s => (
              <div key={s.label} className="bg-white border border-slate-200 p-4 rounded-sm shadow-sm">
                <p className="text-xs text-slate-500 font-medium">{s.label}</p>
                <p className="text-xl font-bold text-slate-900 mt-1">{s.value}</p>
              </div>
            ))}
            <div className="bg-white border border-slate-200 p-4 rounded-sm shadow-sm">
              <p className="text-xs text-slate-500 font-medium mb-1">Deployment Risk</p>
              <p className={`font-semibold text-sm ${riskCls[deploymentRisk] || 'text-slate-400'}`}>
                {deploymentRisk || 'Unknown'}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Past analyses */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <p className="text-sm font-semibold text-slate-700">Past Analyses</p>
          {history.length > 0 && (
            <button
              onClick={clearHistory}
              disabled={clearing}
              className="text-xs text-slate-400 hover:text-red-500 transition-colors disabled:opacity-40"
            >
              {clearing ? 'Clearing...' : 'Clear History'}
            </button>
          )}
        </div>

        {loading && (
          <p className="text-sm text-slate-400 text-center py-8">Loading history...</p>
        )}

        {!loading && history.length === 0 && (
          <div className="text-center py-8 text-slate-400 border border-dashed border-slate-300 bg-white rounded-sm">
            No past analyses for this repository.
          </div>
        )}

        {!loading && history.length > 0 && (
          <div className="space-y-3">
            {history.map((entry, i) => (
              <div key={entry.id || i}>
                <div className={`bg-white border rounded-sm shadow-sm transition-colors ${
                  expandedId === entry.id ? 'border-orange-300' : 'border-slate-200 hover:border-slate-300'
                }`}>
                  <div className="p-4">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap mb-1.5">
                          <span className="text-xs text-slate-400 tabular-nums">{entry.timestamp}</span>
                          <span className="text-xs bg-slate-100 border border-slate-200 text-slate-500 px-2 py-0.5 rounded-sm">{entry.type}</span>
                          {i === 0 && (
                            <span className="text-xs bg-orange-100 text-orange-700 px-2 py-0.5 rounded-sm border border-orange-300 font-semibold">
                              Latest
                            </span>
                          )}
                        </div>
                        <p className="text-sm text-slate-600 leading-relaxed">{entry.summary}</p>
                        <div className="mt-2 max-w-52">
                          <ScoreBar score={entry.score} />
                        </div>
                      </div>

                      {/* Actions */}
                      <div className="flex items-center gap-2 shrink-0">
                        {entry.id && (
                          <button
                            onClick={() => toggleExpand(entry.id)}
                            className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold border transition-colors rounded-sm ${
                              expandedId === entry.id
                                ? 'bg-orange-500 border-orange-500 text-white hover:bg-orange-600'
                                : 'bg-white border-slate-300 text-slate-600 hover:bg-orange-50 hover:border-orange-400 hover:text-orange-600'
                            }`}
                          >
                            {expandedId === entry.id ? '▲ Hide Report' : '▼ View Report'}
                          </button>
                        )}
                        <DownloadButton entry={entry} />
                      </div>
                    </div>
                  </div>
                </div>

                {/* Inline full report */}
                {expandedId === entry.id && entry.id && (
                  <InlineReport
                    entryId={entry.id}
                    onClose={() => setExpandedId(null)}
                  />
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
