import { useState } from 'react'

const CRITICAL_KEYWORDS = ['loss', 'drift', 'violation', 'missing', 'failed', 'security', 'error handling', 'testing']

function isCritical(type = '') {
  return CRITICAL_KEYWORDS.some(w => type.toLowerCase().includes(w))
}

function isSecurity(type = '') {
  return type.toLowerCase().includes('security')
}

function TypeBadge({ type }) {
  const sec = isSecurity(type)
  const crit = isCritical(type)
  return (
    <span className={`text-xs px-2 py-0.5 font-semibold rounded-sm border ${
      sec
        ? 'bg-rose-100 text-rose-700 border-rose-300'
        : crit
        ? 'bg-red-100 text-red-700 border-red-300'
        : 'bg-slate-100 text-slate-600 border-slate-300'
    }`}>
      {type || 'Issue'}
    </span>
  )
}

function IssueCard({ issue }) {
  const [open, setOpen] = useState(false)
  const sec = isSecurity(issue.type)
  const crit = isCritical(issue.type)

  return (
    <div className={`border rounded-sm shadow-sm transition-all ${
      sec ? 'border-rose-300 bg-rose-50' : crit ? 'border-red-200 bg-red-50' : 'border-slate-200 bg-white'
    }`}>
      <button
        className="w-full text-left px-4 py-3 flex items-start gap-3"
        onClick={() => setOpen(o => !o)}
      >
        <span className="mt-0.5 text-sm">{sec ? '🔒' : crit ? '🚨' : 'ℹ️'}</span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <TypeBadge type={issue.type} />
          </div>
          <p className="text-sm text-slate-700 mt-1.5 line-clamp-2">
            {issue.description}
          </p>
        </div>
        <span className="text-slate-400 shrink-0 mt-0.5">{open ? '▲' : '▼'}</span>
      </button>

      {open && (
        <div className="px-4 pb-4 space-y-3 border-t border-slate-200 pt-3">
          {issue.evidence && (
            <div>
              <p className="text-xs text-slate-500 mb-1 font-semibold uppercase tracking-wide">Where in code</p>
              <code className="text-xs text-slate-700 bg-slate-100 border border-slate-200 px-2 py-1.5 block rounded-sm whitespace-pre-wrap">{issue.evidence}</code>
            </div>
          )}
          {issue.reasoning && (
            <div>
              <p className="text-xs text-slate-500 mb-1 font-semibold uppercase tracking-wide">Why it matters</p>
              <p className="text-sm text-slate-600 leading-relaxed">{issue.reasoning}</p>
            </div>
          )}
          {issue.remediation && (
            <div className="bg-blue-50 border border-blue-200 p-3 rounded-sm">
              <p className="text-xs text-blue-700 mb-1 font-semibold uppercase tracking-wide">Recommended Fix</p>
              <p className="text-sm text-blue-800 leading-relaxed">{issue.remediation}</p>
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
      <div className="flex flex-col items-center justify-center h-48 text-slate-400 bg-white border border-slate-200 rounded-sm">
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
        <p className="text-sm text-slate-600">
          {issues.length} issue{issues.length !== 1 ? 's' : ''} found
          {critical.length > 0 && (
            <span className="ml-2 text-red-600 font-medium">({critical.length} critical)</span>
          )}
        </p>
        <div className="flex gap-1">
          {['all', 'critical', 'minor'].map(f => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`text-xs px-3 py-1 capitalize transition-all font-medium uppercase tracking-wide rounded-sm ${
                filter === f
                  ? 'bg-orange-500 text-white shadow-sm'
                  : 'bg-white text-slate-500 hover:text-slate-800 border border-slate-300'
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
