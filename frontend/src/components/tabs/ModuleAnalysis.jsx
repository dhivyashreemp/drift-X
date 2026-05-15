import { useState } from 'react'

const SEVERITY_STYLES = {
  Critical: { badge: 'bg-red-900/60 text-red-400 border-red-700/60', border: 'border-red-700/50 bg-red-950/20', icon: '🔴' },
  High:     { badge: 'bg-orange-900/60 text-orange-400 border-orange-700/60', border: 'border-orange-700/50 bg-orange-950/20', icon: '🟠' },
  Medium:   { badge: 'bg-amber-900/60 text-amber-400 border-amber-700/60', border: 'border-amber-700/50 bg-amber-950/20', icon: '🟡' },
  Low:      { badge: 'bg-zinc-700/60 text-zinc-400 border-zinc-600/60', border: 'border-zinc-700 bg-zinc-800/50', icon: '🔵' },
}

function inferSeverity(issue) {
  if (issue.severity && SEVERITY_STYLES[issue.severity]) return issue.severity
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

function IssueCard({ issue }) {
  const [open, setOpen] = useState(false)
  const severity = inferSeverity(issue)
  const styles = SEVERITY_STYLES[severity]

  return (
    <div className={`border rounded-sm shadow-sm ${styles.border}`}>
      <button className="w-full text-left px-4 py-3 flex items-start gap-3" onClick={() => setOpen(o => !o)}>
        <span className="text-base shrink-0 mt-0.5">{styles.icon}</span>
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap gap-2 mb-1">
            <span className={`text-xs px-2 py-0.5 font-bold border rounded-sm ${styles.badge}`}>{severity}</span>
            {issue.type && (
              <span className="text-xs px-2 py-0.5 bg-zinc-700/60 text-zinc-400 border border-zinc-600/60 rounded-sm font-semibold">{issue.type}</span>
            )}
          </div>
          <p className="text-sm text-zinc-300 line-clamp-2">{issue.description}</p>
        </div>
        <span className="text-zinc-600 shrink-0 text-xs mt-1">{open ? '▲' : '▼'}</span>
      </button>

      {open && (
        <div className="border-t border-zinc-700 divide-y divide-zinc-800">
          <SectionBlock label="What's wrong" icon="📋">
            <p className="text-sm text-zinc-300 leading-relaxed">{issue.description}</p>
          </SectionBlock>
          <SectionBlock label="Where in code" icon="📍">
            <div className="text-sm text-zinc-300">{renderBlocks(issue.evidence)}</div>
          </SectionBlock>
          <SectionBlock label="Why it matters" icon="⚠️">
            <p className="text-sm text-zinc-400 leading-relaxed">{issue.reasoning}</p>
          </SectionBlock>
          <SectionBlock label="Recommended Fix" icon="🔧" highlight>
            <div className="text-sm text-neon-400 leading-relaxed">{renderBlocks(issue.remediation)}</div>
          </SectionBlock>
        </div>
      )}
    </div>
  )
}

function SectionBlock({ label, icon, children, highlight }) {
  return (
    <div className={`px-4 py-3 ${highlight ? 'bg-neon-500/5' : ''}`}>
      <p className="text-xs font-bold text-zinc-500 uppercase tracking-wider mb-2 flex items-center gap-1.5">
        <span>{icon}</span> {label}
      </p>
      {children}
    </div>
  )
}

function MetricCard({ label, value, scoreColor }) {
  return (
    <div className="bg-zinc-800 border border-zinc-700 rounded-sm p-4 text-center">
      <p className={`text-2xl font-bold ${scoreColor || 'text-zinc-100'}`}>{value}</p>
      <p className="text-xs text-zinc-500 mt-1">{label}</p>
    </div>
  )
}

export default function ModuleAnalysis({ moduleResults }) {
  const [filesOpen, setFilesOpen] = useState(false)
  const [usagesOpen, setUsagesOpen] = useState(false)

  if (!moduleResults) return null

  const analysis = moduleResults.analysis ?? {}
  const modScore = analysis.compliance_score
  const scoreColor = modScore >= 85 ? 'text-green-400' : modScore >= 65 ? 'text-amber-400' : 'text-red-400'

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="bg-zinc-800 border border-zinc-700 rounded-sm p-4 shadow-sm">
        <div className="flex items-start gap-3">
          <span className="text-2xl">🧩</span>
          <div>
            <p className="text-xs font-bold text-zinc-500 uppercase tracking-wider">Module Analysis</p>
            <h2 className="text-lg font-bold text-zinc-100 mt-0.5">{moduleResults.module_name}</h2>
            {analysis.module_purpose && (
              <p className="text-sm text-zinc-400 mt-1 leading-relaxed">{analysis.module_purpose}</p>
            )}
          </div>
        </div>
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-3 gap-3">
        <MetricCard label="Files Found" value={moduleResults.file_count} />
        <MetricCard label="Referenced In" value={`${moduleResults.usage_count} file(s)`} />
        <MetricCard label="Module Score" value={modScore != null ? `${Math.round(modScore)} / 100` : 'N/A'} scoreColor={scoreColor} />
      </div>

      {/* Summary */}
      {analysis.summary && (
        <div className="bg-zinc-800 border border-zinc-700 rounded-sm p-4 shadow-sm">
          <p className="text-xs font-bold text-zinc-500 uppercase tracking-wider mb-2">Summary</p>
          {renderBullets(analysis.summary)}
        </div>
      )}

      {/* Key Components */}
      {analysis.key_components?.length > 0 && (
        <div className="bg-zinc-800 border border-zinc-700 rounded-sm p-4 shadow-sm">
          <p className="text-xs font-bold text-zinc-500 uppercase tracking-wider mb-3">Key Components</p>
          <div className="flex flex-wrap gap-2">
            {analysis.key_components.map((c, i) => (
              <span key={i} className="text-xs bg-neon-500/10 border border-neon-500/30 text-neon-500 px-2 py-1 rounded-sm font-mono">
                {c}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Module Files */}
      {moduleResults.related_files?.length > 0 && (
        <div className="bg-zinc-800 border border-zinc-700 rounded-sm shadow-sm">
          <button
            className="w-full text-left px-4 py-3 flex items-center justify-between hover:bg-zinc-700/30 transition-colors"
            onClick={() => setFilesOpen(o => !o)}
          >
            <span className="text-sm font-semibold text-zinc-300">
              📂 Module Files <span className="text-zinc-500 font-normal">({moduleResults.related_files.length})</span>
            </span>
            <span className="text-zinc-500 text-xs">{filesOpen ? '▲' : '▼'}</span>
          </button>
          {filesOpen && (
            <div className="px-4 pb-4 space-y-1 border-t border-zinc-700">
              {moduleResults.related_files.map((f, i) => (
                <code key={i} className="block text-xs text-zinc-400 bg-zinc-900/50 border border-zinc-700 px-2 py-1 mt-1 rounded-sm font-mono">
                  {f}
                </code>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Cross-references */}
      {Object.keys(moduleResults.usage_in_files ?? {}).length > 0 && (
        <div className="bg-zinc-800 border border-zinc-700 rounded-sm shadow-sm">
          <button
            className="w-full text-left px-4 py-3 flex items-center justify-between hover:bg-zinc-700/30 transition-colors"
            onClick={() => setUsagesOpen(o => !o)}
          >
            <span className="text-sm font-semibold text-zinc-300">
              🔗 Cross-References <span className="text-zinc-500 font-normal">({Object.keys(moduleResults.usage_in_files).length} file(s))</span>
            </span>
            <span className="text-zinc-500 text-xs">{usagesOpen ? '▲' : '▼'}</span>
          </button>
          {usagesOpen && (
            <div className="px-4 pb-4 space-y-3 border-t border-zinc-700">
              {Object.entries(moduleResults.usage_in_files).map(([path, hits]) => (
                <div key={path} className="mt-3">
                  <code className="text-xs text-neon-500 font-mono font-semibold">{path}</code>
                  {hits.map((h, i) => (
                    <code key={i} className="block text-xs text-zinc-500 mt-1 bg-zinc-900/50 border border-zinc-700 px-2 py-1 rounded-sm font-mono">
                      L{h.line}: {h.content}
                    </code>
                  ))}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Issues */}
      {analysis.issues?.length > 0 ? (
        <div>
          <p className="text-xs font-bold text-zinc-500 uppercase tracking-wider mb-3">Module Issues ({analysis.issues.length})</p>
          <div className="space-y-2">
            {[...analysis.issues]
              .sort((a, b) => {
                const order = { Critical: 0, High: 1, Medium: 2, Low: 3 }
                return (order[inferSeverity(a)] ?? 9) - (order[inferSeverity(b)] ?? 9)
              })
              .map((issue, i) => (
                <IssueCard key={i} issue={issue} />
              ))}
          </div>
        </div>
      ) : analysis.summary ? (
        <div className="bg-green-950/30 border border-green-700/50 rounded-sm p-4 flex items-start gap-2">
          <span className="text-lg">✅</span>
          <p className="text-sm text-green-400 leading-relaxed">{analysis.summary}</p>
        </div>
      ) : null}
    </div>
  )
}
