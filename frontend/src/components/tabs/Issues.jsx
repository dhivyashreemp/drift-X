import { useState } from 'react'

const SEVERITY_ORDER = { Critical: 0, High: 1, Medium: 2, Low: 3 }

const SEVERITY_STYLES = {
  Critical: { badge: 'bg-red-900/60 text-red-400 border-red-700/60', border: 'border-red-700/50 bg-red-950/20', icon: '🔴' },
  High:     { badge: 'bg-orange-900/60 text-orange-400 border-orange-700/60', border: 'border-orange-700/50 bg-orange-950/20', icon: '🟠' },
  Medium:   { badge: 'bg-amber-900/60 text-amber-400 border-amber-700/60', border: 'border-amber-700/50 bg-amber-950/20', icon: '🟡' },
  Low:      { badge: 'bg-zinc-700/60 text-zinc-400 border-zinc-600/60', border: 'border-zinc-700 bg-zinc-800/50', icon: '🔵' },
}

const TYPE_STYLES = {
  'Security Vulnerability': 'bg-rose-900/50 text-rose-400 border-rose-700/50',
  'Requirement Drift':      'bg-purple-900/50 text-purple-400 border-purple-700/50',
  'Feature Completeness':   'bg-indigo-900/50 text-indigo-400 border-indigo-700/50',
  'Code Quality':           'bg-zinc-700/50 text-zinc-400 border-zinc-600/50',
  'Error Handling':         'bg-red-900/50 text-red-400 border-red-700/50',
  'Testing Gap':            'bg-yellow-900/50 text-yellow-400 border-yellow-700/50',
  'Guideline Violation':    'bg-pink-900/50 text-pink-400 border-pink-700/50',
  'Performance Issue':      'bg-cyan-900/50 text-cyan-400 border-cyan-700/50',
  'Deployment Readiness':   'bg-teal-900/50 text-teal-400 border-teal-700/50',
  'Observability Gap':      'bg-blue-900/50 text-blue-400 border-blue-700/50',
  'Dependency Risk':        'bg-orange-900/50 text-orange-400 border-orange-700/50',
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
        <pre key={i} className="bg-zinc-950 text-zinc-200 text-xs rounded p-3 overflow-x-auto my-2 leading-relaxed border border-zinc-800">
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
  const style = TYPE_STYLES[type] || 'bg-zinc-700/50 text-zinc-400 border-zinc-600/50'
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
          <p className="text-sm text-zinc-300 leading-snug line-clamp-2">
            {issue.description}
          </p>
        </div>
        <span className="text-zinc-600 shrink-0 text-xs mt-1">{open ? '▲' : '▼'}</span>
      </button>

      {open && (
        <div className="border-t border-zinc-700 divide-y divide-zinc-800">
          <Section label="What's wrong" icon="📋">
            <p className="text-sm text-zinc-300 leading-relaxed">{issue.description}</p>
          </Section>

          <Section label="Where in code" icon="📍">
            <div className="text-sm text-zinc-300 leading-relaxed">
              {renderBlocks(issue.evidence)}
            </div>
          </Section>

          <Section label="Why it matters" icon="⚠️">
            <p className="text-sm text-zinc-400 leading-relaxed">{issue.reasoning}</p>
          </Section>

          <Section label="Recommended Fix" icon="🔧" highlight>
            <div className="text-sm text-neon-400 leading-relaxed">
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
    <div className={`px-4 py-3 ${highlight ? 'bg-neon-500/5' : ''}`}>
      <p className="text-xs font-bold text-zinc-500 uppercase tracking-wider mb-2 flex items-center gap-1.5">
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
      <div className="flex flex-col items-center justify-center h-48 text-zinc-500 bg-zinc-800 border border-zinc-700 rounded-sm">
        <p className="text-3xl mb-2">✅</p>
        <p className="font-medium text-zinc-300">No issues found — code looks clean!</p>
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
            filter === sev ? 'ring-2 ring-neon-500/60' : ''
          } ${SEVERITY_STYLES[sev].border}`}
            onClick={() => setFilter(f => f === sev ? 'all' : sev)}
          >
            <p className="text-lg font-bold text-zinc-100">{n}</p>
            <p className="text-xs text-zinc-500 mt-0.5">{sev}</p>
          </div>
        ))}
      </div>

      {/* Filter bar */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-zinc-400">
          Showing <span className="font-semibold text-zinc-200">{displayed.length}</span> of{' '}
          <span className="font-semibold text-zinc-200">{issues.length}</span> issues
          {filter !== 'all' && <span className="ml-1 text-zinc-500">(filtered: {filter})</span>}
        </p>
        <div className="flex gap-1">
          {FILTERS.map(f => (
            <button
              key={f.key}
              onClick={() => setFilter(f.key)}
              className={`text-xs px-3 py-1 font-semibold uppercase tracking-wide rounded-sm transition-all ${
                filter === f.key
                  ? 'bg-neon-500 text-zinc-900 shadow-sm'
                  : 'bg-zinc-800 text-zinc-400 border border-zinc-700 hover:text-zinc-200'
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
