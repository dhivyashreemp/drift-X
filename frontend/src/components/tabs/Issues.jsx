import { useState } from 'react'

const CRITICAL_KEYWORDS = ['loss', 'drift', 'violation', 'missing', 'failed']

function isCritical(type = '') {
  return CRITICAL_KEYWORDS.some(w => type.toLowerCase().includes(w))
}

function TypeBadge({ type }) {
  const critical = isCritical(type)
  return (
    <span className={`text-xs px-2 py-0.5 font-medium ${
      critical
        ? 'bg-red-900/60 text-red-300 border border-red-800'
        : 'bg-navy-700 text-slate-300 border border-navy-600'
    }`}>
      {type || 'Issue'}
    </span>
  )
}

function IssueCard({ issue }) {
  const [open, setOpen] = useState(false)
  const critical = isCritical(issue.type)

  return (
    <div className={`border transition-all ${
      critical ? 'border-red-900 bg-red-950/20' : 'border-navy-700 bg-navy-900'
    }`}>
      <button
        className="w-full text-left px-4 py-3 flex items-start gap-3"
        onClick={() => setOpen(o => !o)}
      >
        <span className="mt-0.5 text-sm">{critical ? '🚨' : 'ℹ️'}</span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <TypeBadge type={issue.type} />
          </div>
          <p className="text-sm text-slate-300 mt-1.5 line-clamp-2">
            {issue.description}
          </p>
        </div>
        <span className="text-slate-600 shrink-0 mt-0.5">{open ? '▲' : '▼'}</span>
      </button>

      {open && (
        <div className="px-4 pb-4 space-y-3 border-t border-navy-700/50 pt-3">
          {issue.evidence && (
            <div>
              <p className="text-xs text-slate-500 mb-1 font-medium">Evidence</p>
              <code className="text-xs text-slate-400 bg-navy-800 px-2 py-1.5 block">{issue.evidence}</code>
            </div>
          )}
          {issue.reasoning && (
            <div>
              <p className="text-xs text-slate-500 mb-1 font-medium">Reasoning</p>
              <p className="text-sm text-slate-400">{issue.reasoning}</p>
            </div>
          )}
          {issue.remediation && (
            <div className="bg-orange-950/20 border border-orange-900/50 p-3">
              <p className="text-xs text-orange-400 mb-1 font-semibold">🤖 AI Remediation</p>
              <p className="text-sm text-orange-300/80">{issue.remediation}</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default function Issues({ issues }) {
  const [filter, setFilter] = useState('all')

  if (!issues || issues.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-48 text-slate-600">
        <p className="text-3xl mb-2">✅</p>
        <p>No issues found — great work!</p>
      </div>
    )
  }

  const critical = issues.filter(i => isCritical(i.type))
  const nonCritical = issues.filter(i => !isCritical(i.type))
  const displayed = filter === 'critical' ? critical : filter === 'minor' ? nonCritical : issues

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-400">
          {issues.length} issue{issues.length !== 1 ? 's' : ''} found
          {critical.length > 0 && (
            <span className="ml-2 text-red-400">({critical.length} critical)</span>
          )}
        </p>
        <div className="flex gap-1">
          {['all', 'critical', 'minor'].map(f => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`text-xs px-3 py-1 capitalize transition-all font-medium uppercase tracking-wide ${
                filter === f
                  ? 'bg-orange-500 text-white shadow-sm shadow-orange-500/20'
                  : 'bg-navy-800 text-slate-400 hover:text-white border border-navy-700'
              }`}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      <div className="space-y-2">
        {displayed.map((issue, i) => (
          <IssueCard key={i} issue={issue} />
        ))}
      </div>
    </div>
  )
}
