import { useState } from 'react'

const SEVERITY_ORDER = { Critical: 0, High: 1, Medium: 2, Low: 3 }

const SEVERITY_STYLES = {
  Critical: { badge: 'bg-red-100 text-red-700 border-red-300', border: 'border-red-300 bg-red-50', icon: '🔴' },
  High:     { badge: 'bg-orange-100 text-orange-700 border-orange-300', border: 'border-orange-200 bg-orange-50', icon: '🟠' },
  Medium:   { badge: 'bg-amber-100 text-amber-700 border-amber-200', border: 'border-amber-200 bg-amber-50', icon: '🟡' },
  Low:      { badge: 'bg-slate-100 text-slate-600 border-slate-300', border: 'border-slate-200 bg-white', icon: '🔵' },
}

const TYPE_STYLES = {
  'Security Vulnerability': 'bg-rose-100 text-rose-700 border-rose-300',
  'Requirement Drift':      'bg-purple-100 text-purple-700 border-purple-200',
  'Feature Completeness':   'bg-indigo-100 text-indigo-700 border-indigo-200',
  'Code Quality':           'bg-slate-100 text-slate-700 border-slate-300',
  'Error Handling':         'bg-red-100 text-red-700 border-red-200',
  'Testing Gap':            'bg-yellow-100 text-yellow-700 border-yellow-200',
  'Guideline Violation':    'bg-pink-100 text-pink-700 border-pink-200',
  'Performance Issue':      'bg-cyan-100 text-cyan-700 border-cyan-200',
  'Deployment Readiness':   'bg-teal-100 text-teal-700 border-teal-200',
  'Observability Gap':      'bg-blue-100 text-blue-700 border-blue-200',
  'Dependency Risk':        'bg-orange-100 text-orange-700 border-orange-200',
}

function inferSeverity(issue) {
  if (issue.severity) return issue.severity
  const t = (issue.type || '').toLowerCase()
  if (t.includes('security')) return 'Critical'
  if (t.includes('loss') || t.includes('drift') || t.includes('error handling') || t.includes('testing')) return 'High'
  if (t.includes('performance') || t.includes('deployment') || t.includes('feature')) return 'Medium'
  return 'Low'
}

function renderBlocks(text) {
  if (!text) return null
  const parts = text.split(/(```[\w]*\n[\s\S]*?```)/g)
  return parts.map((part, i) => {
    const codeMatch = part.match(/^```(\w*)\n([\s\S]*?)```$/)
    if (codeMatch) {
      return (
        <pre key={i} className="bg-slate-900 text-slate-100 text-xs rounded p-3 overflow-x-auto my-2 leading-relaxed">
          <code>{codeMatch[2]}</code>
        </pre>
      )
    }
    if (!part.trim()) return null
    return (
      <span key={i} className="whitespace-pre-wrap">{part}</span>
    )
  })
}

function SeverityBadge({ severity }) {
  const s = SEVERITY_STYLES[severity] || SEVERITY_STYLES.Low
  return (
    <span className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 font-bold border rounded-sm ${s.badge}`}>
      {s.icon} {severity}
    </span>
  )
}

function TypeBadge({ type }) {
  const style = TYPE_STYLES[type] || 'bg-slate-100 text-slate-600 border-slate-300'
  return (
    <span className={`text-xs px-2 py-0.5 font-semibold border rounded-sm ${style}`}>
      {type || 'Issue'}
    </span>
  )
}

function IssueCard({ issue, index }) {
  const [open, setOpen] = useState(false)
  const severity = inferSeverity(issue)
  const styles = SEVERITY_STYLES[severity] || SEVERITY_STYLES.Low

  return (
    <div className={`border rounded-sm shadow-sm transition-shadow hover:shadow-md ${styles.border}`}>
      <button
        className="w-full text-left px-4 py-3.5 flex items-start gap-3"
        onClick={() => setOpen(o => !o)}
      >
        <span className="text-base shrink-0 mt-0.5">{styles.icon}</span>
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-2 mb-1.5">
            <SeverityBadge severity={severity} />
            <TypeBadge type={issue.type} />
          </div>
          <p className="text-sm text-slate-700 leading-snug line-clamp-2">
            {issue.description}
          </p>
        </div>
        <span className="text-slate-400 shrink-0 text-xs mt-1">{open ? '▲' : '▼'}</span>
      </button>

      {open && (
        <div className="border-t border-slate-200 divide-y divide-slate-100">
          <Section label="What's wrong" icon="📋">
            <p className="text-sm text-slate-700 leading-relaxed">{issue.description}</p>
          </Section>

          <Section label="Where in code" icon="📍">
            <div className="text-sm text-slate-700 leading-relaxed">
              {renderBlocks(issue.evidence)}
            </div>
          </Section>

          <Section label="Why it matters" icon="⚠️">
            <p className="text-sm text-slate-600 leading-relaxed">{issue.reasoning}</p>
          </Section>

          <Section label="How to fix" icon="🔧" highlight>
            <div className="text-sm text-blue-800 leading-relaxed">
              {renderBlocks(issue.remediation)}
            </div>
          </Section>
        </div>
      )}
    </div>
  )
}

function Section({ label, icon, children, highlight }) {
  return (
    <div className={`px-4 py-3 ${highlight ? 'bg-blue-50' : ''}`}>
      <p className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2 flex items-center gap-1.5">
        <span>{icon}</span> {label}
      </p>
      {children}
    </div>
  )
}

const FILTERS = [
  { key: 'all', label: 'All' },
  { key: 'Critical', label: 'Critical' },
  { key: 'High', label: 'High' },
  { key: 'Medium', label: 'Medium' },
  { key: 'Low', label: 'Low' },
]

export default function Issues({ issues }) {
  const [filter, setFilter] = useState('all')

  if (!issues || issues.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-48 text-slate-400 bg-white border border-slate-200 rounded-sm">
        <p className="text-3xl mb-2">✅</p>
        <p className="font-medium">No issues found — code looks clean!</p>
      </div>
    )
  }

  const sorted = [...issues].sort((a, b) =>
    (SEVERITY_ORDER[inferSeverity(a)] ?? 9) - (SEVERITY_ORDER[inferSeverity(b)] ?? 9)
  )

  const counts = { Critical: 0, High: 0, Medium: 0, Low: 0 }
  sorted.forEach(i => { counts[inferSeverity(i)] = (counts[inferSeverity(i)] || 0) + 1 })

  const displayed = filter === 'all' ? sorted : sorted.filter(i => inferSeverity(i) === filter)

  return (
    <div className="space-y-4">
      {/* Summary bar */}
      <div className="grid grid-cols-4 gap-2">
        {Object.entries(counts).map(([sev, n]) => (
          <div key={sev} className={`border rounded-sm p-2.5 text-center cursor-pointer transition-all ${
            filter === sev ? 'ring-2 ring-orange-400' : ''
          } ${SEVERITY_STYLES[sev].border}`}
            onClick={() => setFilter(f => f === sev ? 'all' : sev)}
          >
            <p className="text-lg font-bold text-slate-800">{n}</p>
            <p className="text-xs text-slate-500 mt-0.5">{sev}</p>
          </div>
        ))}
      </div>

      {/* Filter bar */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-600">
          Showing <span className="font-semibold">{displayed.length}</span> of{' '}
          <span className="font-semibold">{issues.length}</span> issues
          {filter !== 'all' && <span className="ml-1 text-slate-400">(filtered: {filter})</span>}
        </p>
        <div className="flex gap-1">
          {FILTERS.map(f => (
            <button
              key={f.key}
              onClick={() => setFilter(f.key)}
              className={`text-xs px-3 py-1 font-semibold uppercase tracking-wide rounded-sm transition-all ${
                filter === f.key
                  ? 'bg-orange-500 text-white shadow-sm'
                  : 'bg-white text-slate-500 border border-slate-300 hover:text-slate-800'
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {/* Issue list */}
      <div className="space-y-2">
        {displayed.map((issue, i) => (
          <IssueCard key={i} issue={issue} index={i} />
        ))}
      </div>
    </div>
  )
}
