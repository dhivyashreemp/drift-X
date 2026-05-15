import { useState } from 'react'

function statusConfig(status = '') {
  const s = status.toLowerCase()
  if (s.includes('loss'))               return { badge: 'bg-red-900/60 text-red-400 border-red-700/60',    card: 'border-red-700/50 bg-red-950/20',    icon: '❌', label: status }
  if (s.includes('regression'))         return { badge: 'bg-red-900/60 text-red-400 border-red-700/60',    card: 'border-red-700/50 bg-red-950/20',    icon: '📉', label: status }
  if (s.includes('missing'))            return { badge: 'bg-red-900/60 text-red-400 border-red-700/60',    card: 'border-red-700/50 bg-red-950/20',    icon: '❓', label: status }
  if (s.includes('api breaking'))       return { badge: 'bg-orange-900/60 text-orange-400 border-orange-700/60', card: 'border-orange-700/50 bg-orange-950/20', icon: '💥', label: status }
  if (s.includes('config drift'))       return { badge: 'bg-orange-900/60 text-orange-400 border-orange-700/60', card: 'border-orange-700/50 bg-orange-950/20', icon: '⚙️', label: status }
  if (s.includes('guideline'))          return { badge: 'bg-pink-900/60 text-pink-400 border-pink-700/60',  card: 'border-pink-700/50 bg-pink-950/20',  icon: '📋', label: status }
  if (s.includes('replacement') || s.includes('preserved')) return { badge: 'bg-amber-900/60 text-amber-400 border-amber-700/60', card: 'border-amber-700/50 bg-amber-950/20', icon: '🔄', label: status }
  if (s.includes('refactor') || s.includes('no loss'))      return { badge: 'bg-blue-900/60 text-blue-400 border-blue-700/60',   card: 'border-blue-700/50 bg-blue-950/20',   icon: '🔀', label: status }
  if (s.includes('updated'))            return { badge: 'bg-blue-900/60 text-blue-400 border-blue-700/60',  card: 'border-blue-700/50 bg-blue-950/20',  icon: '✏️', label: status }
  return { badge: 'bg-zinc-700/60 text-zinc-400 border-zinc-600', card: 'border-zinc-700 bg-zinc-800/50', icon: 'ℹ️', label: status }
}

const SEVERITY_COLORS = {
  Critical: 'text-red-400 font-bold',
  High:     'text-orange-400 font-semibold',
  Medium:   'text-amber-400',
  Low:      'text-zinc-500',
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
        <pre key={i} className="bg-zinc-950 text-zinc-200 text-xs rounded p-3 overflow-x-auto my-2 leading-relaxed border border-zinc-800">
          <code>{codeMatch[2]}</code>
        </pre>
      )
    }
    if (!part.trim()) return null
    return <span key={i} className="whitespace-pre-wrap">{part}</span>
  })
}

function renderBullets(text) {
  if (!text) return null
  const trimmed = text.trim()
  if (!trimmed.includes('\n- ') && !trimmed.startsWith('- ')) {
    return <p className="text-sm text-zinc-400 leading-relaxed">{trimmed}</p>
  }
  const lines = trimmed.split('\n').filter(l => l.trim())
  return (
    <ul className="space-y-1.5">
      {lines.map((line, i) => {
        const clean = line.startsWith('- ') ? line.slice(2) : line
        return (
          <li key={i} className="flex items-start gap-2 text-sm text-zinc-400 leading-relaxed">
            <span className="text-neon-500 shrink-0 font-bold mt-0.5">•</span>
            <span>{clean}</span>
          </li>
        )
      })}
    </ul>
  )
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
            <span className="font-semibold text-sm text-zinc-200">{change.feature_name}</span>
            <span className={`text-xs px-2 py-0.5 border font-semibold rounded-sm ${cfg.badge}`}>{change.status}</span>
            {change.severity && (
              <span className={`text-xs ${SEVERITY_COLORS[change.severity] || 'text-zinc-500'}`}>
                {change.severity}
              </span>
            )}
          </div>
          {change.impact && (
            <p className="text-xs text-zinc-500 line-clamp-1">{change.impact}</p>
          )}
          {change.requirement_reference && (
            <p className="text-xs text-indigo-400 mt-0.5 truncate">
              Requirement: {change.requirement_reference}
            </p>
          )}
        </div>
        <span className="text-zinc-600 shrink-0 text-xs mt-1">{open ? '▲' : '▼'}</span>
      </button>

      {open && (
        <div className="border-t border-zinc-700 divide-y divide-zinc-800">
          {change.impact && (
            <Section label="Business Impact" icon="📊">
              <p className="text-sm text-zinc-400 leading-relaxed">{change.impact}</p>
            </Section>
          )}
          {change.requirement_reference && (
            <Section label="Maps to Requirement" icon="📐">
              <p className="text-sm text-indigo-400 leading-relaxed">{change.requirement_reference}</p>
            </Section>
          )}
          {change.commit_info && (
            <Section label="Commit" icon="🔗">
              <code className="text-xs text-zinc-400 bg-zinc-800 border border-zinc-700 px-2 py-1 rounded-sm font-mono block">{change.commit_info}</code>
            </Section>
          )}
          {change.evidence && (
            <Section label="Evidence" icon="📍">
              <div className="text-sm text-zinc-300">{renderBlocks(change.evidence)}</div>
            </Section>
          )}
          {change.reasoning && (
            <Section label="Production Risk" icon="⚠️">
              <p className="text-sm text-zinc-400 leading-relaxed">{change.reasoning}</p>
            </Section>
          )}
          {change.replacement_logic && change.replacement_logic !== 'None' && (
            <Section label="Replacement Logic" icon="🔄" amber>
              <p className="text-sm text-amber-400 leading-relaxed">{change.replacement_logic}</p>
            </Section>
          )}
          {problematic && change.remediation && (
            <Section label="Recommended Fix" icon="🔧" highlight>
              <div className="text-sm text-neon-400 leading-relaxed">{renderBlocks(change.remediation)}</div>
            </Section>
          )}
        </div>
      )}
    </div>
  )
}

function Section({ label, icon, children, highlight, amber }) {
  const bg = highlight ? 'bg-neon-500/5' : amber ? 'bg-amber-950/20' : ''
  return (
    <div className={`px-4 py-3 ${bg}`}>
      <p className="text-xs font-bold text-zinc-500 uppercase tracking-wider mb-2 flex items-center gap-1.5">
        <span>{icon}</span> {label}
      </p>
      {children}
    </div>
  )
}

export default function FeatureEvolution({ historyResults }) {
  const [filter, setFilter] = useState('all')

  if (!historyResults || historyResults.error) {
    return (
      <div className="text-zinc-500 text-center py-12 bg-zinc-800 border border-zinc-700 rounded-sm">
        No feature evolution data available.
      </div>
    )
  }

  const changes = historyResults.feature_changes ?? []
  const metadata = historyResults.analysis_metadata ?? {}

  if (changes.length === 0) {
    return (
      <div className="text-center py-12 text-zinc-500 bg-zinc-800 border border-zinc-700 rounded-sm">
        <p className="text-2xl mb-2">✅</p>
        <p className="text-zinc-300">No feature changes detected in this commit range.</p>
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
          <p className="text-sm text-zinc-400 font-medium">{changes.length} change{changes.length !== 1 ? 's' : ''} tracked</p>
          {problems.length > 0 && (
            <span className="text-xs bg-red-900/60 text-red-400 border border-red-700/50 px-2 py-0.5 rounded-sm font-semibold">
              {problems.length} problem{problems.length !== 1 ? 's' : ''}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {(metadata.base_commit || metadata.head_commit) && (
            <span className="text-xs text-zinc-500 font-mono bg-zinc-800 border border-zinc-700 px-2 py-1 rounded-sm">
              {String(metadata.base_commit ?? '').slice(0, 8)} → {String(metadata.head_commit ?? '').slice(0, 8)}
            </span>
          )}
          {['all', 'problems', 'safe'].map(f => (
            <button key={f} onClick={() => setFilter(f)}
              className={`text-xs px-3 py-1 font-semibold capitalize rounded-sm border transition-all ${
                filter === f
                  ? 'bg-neon-500 text-zinc-900 border-neon-500'
                  : 'bg-zinc-800 text-zinc-500 border-zinc-700 hover:text-zinc-200'
              }`}
            >
              {f === 'problems' ? `Problems (${problems.length})` : f === 'safe' ? `Safe (${safe.length})` : `All (${changes.length})`}
            </button>
          ))}
        </div>
      </div>

      {/* Summary */}
      {historyResults.summary && (
        <div className="bg-zinc-800 border border-zinc-700 rounded-sm p-4 shadow-sm">
          <p className="text-xs font-bold text-zinc-500 uppercase tracking-wider mb-2">Evolution Summary</p>
          {renderBullets(historyResults.summary)}
        </div>
      )}

      {/* Status type legend */}
      <div className="flex flex-wrap gap-2">
        {[
          { label: 'Loss / Missing / Regression', color: 'bg-red-900/60 text-red-400 border-red-700/60' },
          { label: 'API Breaking / Config Drift', color: 'bg-orange-900/60 text-orange-400 border-orange-700/60' },
          { label: 'Replacement / Preserved',    color: 'bg-amber-900/60 text-amber-400 border-amber-700/60' },
          { label: 'Refactor / No Loss',          color: 'bg-blue-900/60 text-blue-400 border-blue-700/60' },
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
