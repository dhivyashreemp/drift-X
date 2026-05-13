import { useState, useEffect, useRef, useCallback } from 'react'
import { useAuth } from '../contexts/AuthContext'

const REFRESH_MS = 15000

function scoreColor(score) {
  if (score == null) return 'text-slate-400'
  if (score >= 80) return 'text-green-600'
  if (score >= 60) return 'text-amber-600'
  return 'text-red-600'
}

function scoreBg(score) {
  if (score == null) return ''
  if (score >= 80) return 'bg-green-50'
  if (score >= 60) return 'bg-amber-50/50'
  return 'bg-red-50/50'
}

function gateLabel(score) {
  if (score == null) return { label: 'No data', cls: 'text-slate-500 bg-slate-100 border-slate-300' }
  if (score >= 80) return { label: 'Pass', cls: 'text-green-700 bg-green-100 border-green-300' }
  if (score >= 60) return { label: 'Warning', cls: 'text-amber-700 bg-amber-100 border-amber-300' }
  return { label: 'Fail', cls: 'text-red-700 bg-red-100 border-red-300' }
}

function timeSince(ts) {
  if (!ts) return '-'
  const diff = Date.now() - new Date(ts).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  return `${Math.floor(hrs / 24)}d ago`
}

function MiniBar({ score }) {
  const s = Math.min(100, Math.max(0, Number(score) || 0))
  const color = s >= 80 ? 'bg-green-500' : s >= 60 ? 'bg-amber-500' : 'bg-red-500'
  return (
    <div className="flex items-center gap-1.5">
      <div className="w-20 bg-slate-200 h-2 rounded-full">
        <div className={`${color} h-2 rounded-full`} style={{ width: `${s}%` }} />
      </div>
    </div>
  )
}

function Trend({ trend, prev, current }) {
  if (!trend || trend === 'flat') return <span className="text-slate-400 text-xs">-</span>
  const up = trend === 'up'
  const diff = current != null && prev != null ? Math.abs(Math.round(current - prev)) : null
  return (
    <span className={`text-xs font-bold ${up ? 'text-green-600' : 'text-red-600'}`}>
      {up ? '↑' : '↓'} {diff != null ? diff : ''}
    </span>
  )
}

function HistoryDrawer({ email, onClose }) {
  const { authFetch } = useAuth()
  const [history, setHistory] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    authFetch(`/api/team/${encodeURIComponent(email)}/history`)
      .then(r => r.json())
      .then(data => setHistory(Array.isArray(data) ? data : []))
      .catch(() => setHistory([]))
      .finally(() => setLoading(false))
  }, [email])

  return (
    <tr>
      <td colSpan={10} className="bg-slate-50 border-t border-b border-orange-200 px-0 py-0">
        <div className="px-6 py-4">
          <div className="flex items-center justify-between mb-3">
            <p className="text-xs font-semibold text-orange-600 uppercase tracking-wide">
              Analysis History — {email}
            </p>
            <button onClick={onClose} className="text-xs text-slate-400 hover:text-slate-800">Close</button>
          </div>

          {loading && <p className="text-xs text-slate-400">Loading...</p>}

          {!loading && (!history || history.length === 0) && (
            <p className="text-xs text-slate-400">No analyses recorded yet.</p>
          )}

          {!loading && history && history.length > 0 && (
            <div className="space-y-2 max-h-96 overflow-y-auto pr-1">
              {history.map((h, i) => (
                <div key={i} className="bg-white border border-slate-200 p-3 hover:border-slate-300 transition-colors rounded-sm">
                  <div className="flex items-center justify-between gap-4 flex-wrap">
                    <div className="flex items-center gap-3 flex-wrap">
                      <span className="text-xs text-slate-400 tabular-nums whitespace-nowrap">{h.timestamp}</span>
                      <span className="text-xs text-slate-700 font-medium">
                        {(h.repo_url || '').replace('https://github.com/', '').replace('https://', '')}
                      </span>
                    </div>
                    <div className="flex items-center gap-3 shrink-0">
                      <div className="flex items-center gap-2">
                        <span className={`text-sm font-bold tabular-nums ${scoreColor(h.score)}`}>{Math.round(h.score)}</span>
                        <MiniBar score={h.score} />
                      </div>
                      {h.issue_count > 0 && (
                        <span className="text-xs text-slate-500 bg-slate-100 border border-slate-200 px-2 py-0.5 rounded-sm">
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
                    <p className="text-xs text-slate-500 mt-2 leading-relaxed border-t border-slate-100 pt-2">
                      {h.summary}
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </td>
    </tr>
  )
}

export default function TeamDashboard() {
  const { user, authFetch } = useAuth()
  const [team, setTeam] = useState([])
  const [loading, setLoading] = useState(true)
  const [lastRefresh, setLastRefresh] = useState(null)
  const [expandedEmail, setExpandedEmail] = useState(null)
  const [sortKey, setSortKey] = useState('latest_score')
  const [sortDir, setSortDir] = useState('desc')
  const [filter, setFilter] = useState('all')
  const pollRef = useRef(null)
  const isManager = user?.role === 'manager'

  const fetchTeam = useCallback(async () => {
    try {
      const res = await authFetch('/api/team')
      const data = await res.json()
      if (Array.isArray(data)) setTeam(data)
      setLastRefresh(new Date())
      setLoading(false)
    } catch (_) {
      setLoading(false)
    }
  }, [authFetch])

  useEffect(() => {
    fetchTeam()
    pollRef.current = setInterval(fetchTeam, REFRESH_MS)
    return () => clearInterval(pollRef.current)
  }, [fetchTeam])

  const handleSort = (key) => {
    if (sortKey === key) setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    else { setSortKey(key); setSortDir('desc') }
  }

  const analyzed = team.filter(d => d.analyses_count > 0)
  const stats = {
    total: team.length,
    compliant: analyzed.filter(d => (d.latest_score || 0) >= 80).length,
    atRisk: analyzed.filter(d => (d.latest_score || 0) < 60).length,
    avgScore: analyzed.length
      ? Math.round(analyzed.reduce((s, d) => s + (d.latest_score || 0), 0) / analyzed.length) : 0,
    activeToday: team.filter(d => d.today_scores?.length > 0).length,
    neverAnalyzed: team.filter(d => d.analyses_count === 0).length,
    weeklyRuns: team.reduce((s, d) => s + (d.this_week_count || 0), 0),
  }

  const filtered = team.filter(d => {
    if (filter === 'at-risk') return d.latest_score != null && d.latest_score < 60
    if (filter === 'compliant') return d.latest_score != null && d.latest_score >= 80
    if (filter === 'inactive') return d.today_scores?.length === 0
    if (filter === 'never') return d.analyses_count === 0
    return true
  })

  const sorted = [...filtered].sort((a, b) => {
    let av = a[sortKey], bv = b[sortKey]
    if (av == null) av = sortDir === 'asc' ? Infinity : -Infinity
    if (bv == null) bv = sortDir === 'asc' ? Infinity : -Infinity
    if (typeof av === 'string') return sortDir === 'asc' ? av.localeCompare(bv) : bv.localeCompare(av)
    return sortDir === 'asc' ? av - bv : bv - av
  })

  const SortTh = ({ col, label }) => (
    <th
      className="text-left py-3 pr-4 text-xs font-semibold text-slate-500 uppercase tracking-wide cursor-pointer hover:text-slate-800 select-none whitespace-nowrap"
      onClick={() => handleSort(col)}
    >
      {label}
      {sortKey === col && <span className="ml-1 text-orange-500">{sortDir === 'asc' ? '↑' : '↓'}</span>}
    </th>
  )

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3 mb-6">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-slate-900">Team Compliance Dashboard</h1>
            {isManager && (
              <span className="text-xs bg-amber-100 text-amber-700 border border-amber-300 px-2 py-1 uppercase tracking-wide font-semibold rounded-sm">
                Manager View
              </span>
            )}
          </div>
          <p className="text-slate-500 text-sm mt-1">
            {team.length} developer{team.length !== 1 ? 's' : ''} · {stats.weeklyRuns} analyses this week
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 bg-green-500 animate-pulse inline-block rounded-full" />
            <span className="text-xs text-slate-400">
              Live · refreshes every 15s
              {lastRefresh && ` · updated ${timeSince(lastRefresh.toISOString())}`}
            </span>
          </div>
          <button
            onClick={fetchTeam}
            className="text-xs text-orange-600 hover:text-orange-700 border border-orange-300 bg-orange-50 hover:bg-orange-100 px-2.5 py-1 transition-colors rounded-sm"
          >
            Refresh
          </button>
        </div>
      </div>

      {/* Stats cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3 mb-6">
        <StatCard label="Total Devs" value={stats.total} />
        <StatCard label="Compliant" value={stats.compliant} color="text-green-600" />
        <StatCard label="At Risk" value={stats.atRisk} color={stats.atRisk > 0 ? 'text-red-600' : 'text-slate-400'} />
        <StatCard label="Avg Score" value={analyzed.length ? `${stats.avgScore}` : '-'} />
        <StatCard label="Active Today" value={stats.activeToday} color="text-orange-600" />
        <StatCard label="This Week" value={stats.weeklyRuns} color="text-orange-600" />
        <StatCard label="Never Run" value={stats.neverAnalyzed} color={stats.neverAnalyzed > 0 ? 'text-amber-600' : 'text-slate-400'} />
      </div>

      {/* At-risk alert */}
      {isManager && stats.atRisk > 0 && (
        <div className="mb-5 bg-red-50 border border-red-300 p-4 rounded-sm">
          <p className="text-sm font-semibold text-red-700 mb-2">
            {stats.atRisk} developer{stats.atRisk !== 1 ? 's' : ''} below compliance threshold — action required
          </p>
          <div className="flex flex-wrap gap-2">
            {analyzed.filter(d => (d.latest_score || 0) < 60).map(d => (
              <span key={d.email} className="text-xs bg-red-100 border border-red-300 px-3 py-1 text-red-700 rounded-sm">
                {d.name} — <strong>{Math.round(d.latest_score)}/100</strong>
                {d.last_critical_count > 0 && <> · {d.last_critical_count} critical</>}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Filter tabs */}
      <div className="flex gap-2 mb-4 flex-wrap">
        {[
          { key: 'all', label: `All (${team.length})` },
          { key: 'at-risk', label: `At Risk (${stats.atRisk})` },
          { key: 'compliant', label: `Compliant (${stats.compliant})` },
          { key: 'inactive', label: `Not Active Today (${team.length - stats.activeToday})` },
          { key: 'never', label: `Never Analyzed (${stats.neverAnalyzed})` },
        ].map(tab => (
          <button
            key={tab.key}
            onClick={() => setFilter(tab.key)}
            className={`px-3 py-1 text-xs border transition-colors uppercase tracking-wide font-medium rounded-sm ${
              filter === tab.key
                ? 'bg-orange-500 border-orange-500 text-white shadow-sm'
                : 'bg-white border-slate-300 text-slate-500 hover:text-slate-800 hover:border-slate-400'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Table */}
      {loading && (
        <div className="text-center py-16 text-slate-400">Loading team data...</div>
      )}

      {!loading && sorted.length === 0 && (
        <div className="text-center py-16 border border-dashed border-slate-300 text-slate-400 bg-white rounded-sm">
          <p className="text-4xl mb-3">👥</p>
          <p>No developers match this filter.</p>
        </div>
      )}

      {!loading && sorted.length > 0 && (
        <div className="bg-white border border-slate-200 overflow-hidden rounded-sm shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="border-b border-slate-200 bg-slate-50">
                <tr>
                  <SortTh col="name" label="Developer" />
                  <SortTh col="latest_score" label="Score" />
                  <th className="text-left py-3 pr-4 text-xs font-semibold text-slate-500 uppercase tracking-wide">Bar</th>
                  <th className="text-left py-3 pr-4 text-xs font-semibold text-slate-500 uppercase tracking-wide">Gate</th>
                  <th className="text-left py-3 pr-4 text-xs font-semibold text-slate-500 uppercase tracking-wide">Trend</th>
                  <SortTh col="last_issue_count" label="Issues" />
                  <SortTh col="last_critical_count" label="Critical" />
                  <th className="text-left py-3 pr-4 text-xs font-semibold text-slate-500 uppercase tracking-wide">Today</th>
                  <SortTh col="analyses_count" label="Total Runs" />
                  <th className="text-left py-3 pr-4 text-xs font-semibold text-slate-500 uppercase tracking-wide">Last Active</th>
                  {isManager && <th className="py-3 pr-4" />}
                </tr>
              </thead>
              <tbody>
                {sorted.map((dev) => {
                  const isMe = dev.email === user?.email
                  const { label: gLabel, cls: gCls } = gateLabel(dev.latest_score)
                  const todayRuns = dev.today_scores?.length || 0
                  const isExpanded = expandedEmail === dev.email
                  const canExpand = isMe || isManager

                  return (
                    <>
                      <tr
                        key={dev.email}
                        className={`border-b border-slate-100 hover:bg-slate-50 transition-colors ${
                          isMe ? 'bg-orange-50/60' : scoreBg(dev.latest_score)
                        }`}
                      >
                        <td className="py-3 pr-4 pl-4">
                          <div className="flex items-center gap-2.5">
                            <div className={`w-8 h-8 flex items-center justify-center text-white text-xs font-bold uppercase shrink-0 rounded-sm ${
                              dev.analyses_count === 0 ? 'bg-slate-400' : 'bg-indigo-600'
                            }`}>
                              {dev.name?.[0] || '?'}
                            </div>
                            <div>
                              <div className="flex items-center gap-1.5">
                                <p className="text-sm font-medium text-slate-900">{dev.name}</p>
                                {isMe && <span className="text-xs text-orange-600 bg-orange-100 border border-orange-300 px-1.5 rounded-sm">you</span>}
                                {dev.analyses_count === 0 && <span className="text-xs text-slate-400 bg-slate-100 px-1.5 border border-slate-200 rounded-sm">new</span>}
                              </div>
                              <p className="text-xs text-slate-400">{dev.email}</p>
                            </div>
                          </div>
                        </td>

                        <td className="py-3 pr-4 tabular-nums">
                          <span className={`text-lg font-bold ${scoreColor(dev.latest_score)}`}>
                            {dev.latest_score != null ? Math.round(dev.latest_score) : '-'}
                          </span>
                          {dev.latest_score != null && <span className="text-xs text-slate-400">/100</span>}
                        </td>

                        <td className="py-3 pr-4">
                          {dev.latest_score != null ? <MiniBar score={dev.latest_score} /> : <span className="text-xs text-slate-300">-</span>}
                        </td>

                        <td className="py-3 pr-4">
                          <span className={`text-xs px-2 py-0.5 border font-medium rounded-sm ${gCls}`}>{gLabel}</span>
                        </td>

                        <td className="py-3 pr-4">
                          <Trend trend={dev.score_trend} prev={dev.prev_score} current={dev.latest_score} />
                        </td>

                        <td className="py-3 pr-4 tabular-nums text-sm text-slate-600">
                          {dev.last_issue_count > 0 ? dev.last_issue_count : <span className="text-slate-300">-</span>}
                        </td>

                        <td className="py-3 pr-4 tabular-nums text-sm">
                          {dev.last_critical_count > 0
                            ? <span className="text-red-600 font-semibold">{dev.last_critical_count}</span>
                            : <span className="text-slate-300">-</span>}
                        </td>

                        <td className="py-3 pr-4">
                          {todayRuns > 0
                            ? <span className="text-xs text-orange-700 bg-orange-100 border border-orange-300 px-2 py-0.5 rounded-sm">{todayRuns} today</span>
                            : <span className="text-xs text-slate-300">idle</span>}
                        </td>

                        <td className="py-3 pr-4 tabular-nums text-sm text-slate-500">
                          {dev.analyses_count > 0 ? dev.analyses_count : <span className="text-slate-300">0</span>}
                        </td>

                        <td className="py-3 pr-4 text-xs text-slate-400 whitespace-nowrap tabular-nums">
                          {timeSince(dev.last_active)}
                        </td>

                        {canExpand && (
                          <td className="py-3 pr-4">
                            <button
                              onClick={() => setExpandedEmail(isExpanded ? null : dev.email)}
                              className="text-xs text-slate-400 hover:text-orange-600 transition-colors whitespace-nowrap"
                            >
                              {isExpanded ? 'hide' : 'history'}
                            </button>
                          </td>
                        )}
                        {!canExpand && <td />}
                      </tr>

                      {isExpanded && (
                        <HistoryDrawer
                          key={`drawer-${dev.email}`}
                          email={dev.email}
                          onClose={() => setExpandedEmail(null)}
                        />
                      )}
                    </>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}

function StatCard({ label, value, color = 'text-slate-900' }) {
  return (
    <div className="bg-white border border-slate-200 p-3 rounded-sm shadow-sm">
      <p className="text-xs text-slate-500 mb-1">{label}</p>
      <p className={`text-xl font-bold ${color}`}>{value}</p>
    </div>
  )
}
