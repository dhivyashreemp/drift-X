import { useState } from 'react'

function statusConfig(status = '') {
  const s = status.toLowerCase()
  if (s.includes('loss'))               return { badge: 'bg-red-100 text-red-700 border-red-300',    card: 'border-red-200 bg-red-50',    icon: '❌', label: status }
  if (s.includes('regression'))         return { badge: 'bg-red-100 text-red-700 border-red-300',    card: 'border-red-200 bg-red-50',    icon: '📉', label: status }
  if (s.includes('missing'))            return { badge: 'bg-red-100 text-red-700 border-red-300',    card: 'border-red-200 bg-red-50',    icon: '❓', label: status }
  if (s.includes('api breaking'))       return { badge: 'bg-orange-100 text-orange-700 border-orange-300', card: 'border-orange-200 bg-orange-50', icon: '💥', label: status }
  if (s.includes('config drift'))       return { badge: 'bg-orange-100 text-orange-700 border-orange-300', card: 'border-orange-200 bg-orange-50', icon: '⚙️', label: status }
  if (s.includes('guideline'))          return { badge: 'bg-pink-100 text-pink-700 border-pink-300',  card: 'border-pink-200 bg-pink-50',  icon: '📋', label: status }
  if (s.includes('replacement') || s.includes('preserved')) return { badge: 'bg-amber-100 text-amber-700 border-amber-200', card: 'border-amber-200 bg-amber-50', icon: '🔄', label: status }
  if (s.includes('refactor') || s.includes('no loss'))      return { badge: 'bg-blue-100 text-blue-700 border-blue-200',   card: 'border-blue-200 bg-blue-50',   icon: '🔀', label: status }
  if (s.includes('updated'))            return { badge: 'bg-blue-100 text-blue-700 border-blue-200',  card: 'border-blue-200 bg-blue-50',  icon: '✏️', label: status }
  return { badge: 'bg-slate-100 text-slate-600 border-slate-300', card: 'border-slate-200 bg-white', icon: 'ℹ️', label: status }
}

const SEVERITY_COLORS = {
  Critical: 'text-red-600 font-bold',
  High:     'text-orange-600 font-semibold',
  Medium:   'text-amber-600',
  Low:      'text-slate-500',
}

function isProblematic(status = '') {
  const s = status.toLowerCase()
  return s.includes('loss') || s.includes('missing') || s.includes('regression') ||
         s.includes('api breaking') || s.includes('config drift') || s.includes('guideline')
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
    return <span key={i} className="whitespace-pre-wrap">{part}</span>
  })
}

function ChangeCard({ change }) {
  const [open, setOpen] = useState(false)
  const cfg = statusConfig(change.status)
  const problematic = isProblematic(change.status)

  return (
    <div className={`border rounded-sm shadow-sm ${cfg.card}`}>
      <button
        className="w-full text-left px-4 py-3.5 flex items-start gap-3"
        onClick={() => setOpen(o => !o)}
      >
        <span className="text-base shrink-0 mt-0.5">{cfg.icon}</span>
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-2 mb-1">
            <span className="font-semibold text-sm text-slate-800">{change.feature_name}</span>
            <span className={`text-xs px-2 py-0.5 border font-semibold rounded-sm ${cfg.badge}`}>{change.status}</span>
            {change.severity && (
              <span className={`text-xs ${SEVERITY_COLORS[change.severity] || 'text-slate-500'}`}>
                {change.severity}
              </span>
            )}
          </div>
          {change.impact && (
            <p className="text-xs text-slate-500 line-clamp-1">{change.impact}</p>
          )}
          {change.requirement_reference && (
            <p className="text-xs text-indigo-500 mt-0.5 truncate">
              Requirement: {change.requirement_reference}
            </p>
          )}
        </div>
        <span className="text-slate-400 shrink-0 text-xs mt-1">{open ? '▲' : '▼'}</span>
      </button>

      {open && (
        <div className="border-t border-slate-200 divide-y divide-slate-100">
          {change.impact && (
            <Section label="Business Impact" icon="📊">
              <p className="text-sm text-slate-600 leading-relaxed">{change.impact}</p>
            </Section>
          )}
          {change.requirement_reference && (
            <Section label="Maps to Requirement" icon="📐">
              <p className="text-sm text-indigo-700 leading-relaxed">{change.requirement_reference}</p>
            </Section>
          )}
          {change.commit_info && (
            <Section label="Commit" icon="🔗">
              <code className="text-xs text-slate-600 bg-slate-100 border border-slate-200 px-2 py-1 rounded-sm font-mono block">{change.commit_info}</code>
            </Section>
          )}
          {change.evidence && (
            <Section label="Evidence" icon="📍">
              <div className="text-sm text-slate-700">{renderBlocks(change.evidence)}</div>
            </Section>
          )}
          {change.reasoning && (
            <Section label="Production Risk" icon="⚠️">
              <p className="text-sm text-slate-600 leading-relaxed">{change.reasoning}</p>
            </Section>
          )}
          {change.replacement_logic && change.replacement_logic !== 'None' && (
            <Section label="Replacement Logic" icon="🔄" amber>
              <p className="text-sm text-amber-800 leading-relaxed">{change.replacement_logic}</p>
            </Section>
          )}
          {problematic && change.remediation && (
            <Section label="How to Restore" icon="🔧" highlight>
              <div className="text-sm text-blue-800 leading-relaxed">{renderBlocks(change.remediation)}</div>
            </Section>
          )}
        </div>
      )}
    </div>
  )
}

function Section({ label, icon, children, highlight, amber }) {
  const bg = highlight ? 'bg-blue-50' : amber ? 'bg-amber-50' : ''
  return (
    <div className={`px-4 py-3 ${bg}`}>
      <p className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2 flex items-center gap-1.5">
        <span>{icon}</span> {label}
      </p>
      {children}
    </div>
  )
}

const PROBLEM_STATUSES = ['Loss', 'Missing', 'Regression', 'API Breaking Change', 'Config Drift', 'Guideline Violation']

export default function FeatureEvolution({ historyResults }) {
  const [filter, setFilter] = useState('all')

  if (!historyResults || historyResults.error) {
    return (
      <div className="text-slate-400 text-center py-12 bg-white border border-slate-200 rounded-sm">
        No feature evolution data available.
      </div>
    )
  }

  const changes = historyResults.feature_changes ?? []
  const metadata = historyResults.analysis_metadata ?? {}

  if (changes.length === 0) {
    return (
      <div className="text-center py-12 text-slate-500 bg-white border border-slate-200 rounded-sm">
        <p className="text-2xl mb-2">✅</p>
        <p>No feature changes detected in this commit range.</p>
      </div>
    )
  }

  const problems = changes.filter(c => isProblematic(c.status))
  const safe = changes.filter(c => !isProblematic(c.status))

  const displayed = filter === 'problems' ? problems : filter === 'safe' ? safe : changes

  return (
    <div className="space-y-4">
      {/* Header bar */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-3">
          <p className="text-sm text-slate-600 font-medium">{changes.length} change{changes.length !== 1 ? 's' : ''} tracked</p>
          {problems.length > 0 && (
            <span className="text-xs bg-red-100 text-red-700 border border-red-300 px-2 py-0.5 rounded-sm font-semibold">
              {problems.length} problem{problems.length !== 1 ? 's' : ''}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {(metadata.base_commit || metadata.head_commit) && (
            <span className="text-xs text-slate-500 font-mono bg-slate-100 border border-slate-200 px-2 py-1 rounded-sm">
              {String(metadata.base_commit ?? '').slice(0, 8)} → {String(metadata.head_commit ?? '').slice(0, 8)}
            </span>
          )}
          {['all', 'problems', 'safe'].map(f => (
            <button key={f} onClick={() => setFilter(f)}
              className={`text-xs px-3 py-1 font-semibold capitalize rounded-sm border transition-all ${
                filter === f ? 'bg-orange-500 text-white border-orange-500' : 'bg-white text-slate-500 border-slate-300 hover:text-slate-800'
              }`}
            >
              {f === 'problems' ? `Problems (${problems.length})` : f === 'safe' ? `Safe (${safe.length})` : `All (${changes.length})`}
            </button>
          ))}
        </div>
      </div>

      {/* Summary */}
      {historyResults.summary && (
        <div className="bg-white border border-slate-200 rounded-sm p-4 shadow-sm">
          <p className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Evolution Summary</p>
          <p className="text-sm text-slate-700 leading-relaxed">{historyResults.summary}</p>
        </div>
      )}

      {/* Status type legend */}
      <div className="flex flex-wrap gap-2">
        {[
          { label: 'Loss / Missing / Regression', color: 'bg-red-100 text-red-700 border-red-300' },
          { label: 'API Breaking / Config Drift', color: 'bg-orange-100 text-orange-700 border-orange-300' },
          { label: 'Replacement / Preserved',    color: 'bg-amber-100 text-amber-700 border-amber-200' },
          { label: 'Refactor / No Loss',          color: 'bg-blue-100 text-blue-700 border-blue-200' },
        ].map(l => (
          <span key={l.label} className={`text-xs px-2 py-0.5 border font-semibold rounded-sm ${l.color}`}>{l.label}</span>
        ))}
      </div>

      {/* Change list */}
      <div className="space-y-2">
        {displayed.map((c, i) => <ChangeCard key={i} change={c} />)}
      </div>
    </div>
  )
}
