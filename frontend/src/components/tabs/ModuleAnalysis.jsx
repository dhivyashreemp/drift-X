import { useState } from 'react'

const SEVERITY_STYLES = {
  Critical: { badge: 'bg-red-100 text-red-700 border-red-300', border: 'border-red-300 bg-red-50', icon: '🔴' },
  High:     { badge: 'bg-orange-100 text-orange-700 border-orange-300', border: 'border-orange-200 bg-orange-50', icon: '🟠' },
  Medium:   { badge: 'bg-amber-100 text-amber-700 border-amber-200', border: 'border-amber-200 bg-amber-50', icon: '🟡' },
  Low:      { badge: 'bg-slate-100 text-slate-600 border-slate-300', border: 'border-slate-200 bg-white', icon: '🔵' },
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
        <pre key={i} className="bg-slate-900 text-slate-100 text-xs rounded p-3 overflow-x-auto my-2 leading-relaxed">
          <code>{codeMatch[2]}</code>
        </pre>
      )
    }
    if (!part.trim()) return null
    return <span key={i} className="whitespace-pre-wrap">{part}</span>
  })
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
              <span className="text-xs px-2 py-0.5 bg-slate-100 text-slate-600 border border-slate-300 rounded-sm font-semibold">{issue.type}</span>
            )}
          </div>
          <p className="text-sm text-slate-700 line-clamp-2">{issue.description}</p>
        </div>
        <span className="text-slate-400 shrink-0 text-xs mt-1">{open ? '▲' : '▼'}</span>
      </button>

      {open && (
        <div className="border-t border-slate-200 divide-y divide-slate-100">
          <SectionBlock label="What's wrong" icon="📋">
            <p className="text-sm text-slate-700 leading-relaxed">{issue.description}</p>
          </SectionBlock>
          <SectionBlock label="Where in code" icon="📍">
            <div className="text-sm text-slate-700">{renderBlocks(issue.evidence)}</div>
          </SectionBlock>
          <SectionBlock label="Why it matters" icon="⚠️">
            <p className="text-sm text-slate-600 leading-relaxed">{issue.reasoning}</p>
          </SectionBlock>
          <SectionBlock label="How to fix" icon="🔧" highlight>
            <div className="text-sm text-blue-800 leading-relaxed">{renderBlocks(issue.remediation)}</div>
          </SectionBlock>
        </div>
      )}
    </div>
  )
}

function SectionBlock({ label, icon, children, highlight }) {
  return (
    <div className={`px-4 py-3 ${highlight ? 'bg-blue-50' : ''}`}>
      <p className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2 flex items-center gap-1.5">
        <span>{icon}</span> {label}
      </p>
      {children}
    </div>
  )
}

function MetricCard({ label, value, scoreColor }) {
  return (
    <div className="bg-slate-50 border border-slate-200 rounded-sm p-4 text-center">
      <p className={`text-2xl font-bold ${scoreColor || 'text-slate-800'}`}>{value}</p>
      <p className="text-xs text-slate-500 mt-1">{label}</p>
    </div>
  )
}

export default function ModuleAnalysis({ moduleResults }) {
  const [filesOpen, setFilesOpen] = useState(false)
  const [usagesOpen, setUsagesOpen] = useState(false)

  if (!moduleResults) return null

  const analysis = moduleResults.analysis ?? {}
  const modScore = analysis.compliance_score
  const scoreColor = modScore >= 85 ? 'text-green-600' : modScore >= 65 ? 'text-amber-600' : 'text-red-600'

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="bg-white border border-slate-200 rounded-sm p-4 shadow-sm">
        <div className="flex items-start gap-3">
          <span className="text-2xl">🧩</span>
          <div>
            <p className="text-xs font-bold text-slate-500 uppercase tracking-wider">Module Analysis</p>
            <h2 className="text-lg font-bold text-slate-800 mt-0.5">{moduleResults.module_name}</h2>
            {analysis.module_purpose && (
              <p className="text-sm text-slate-500 mt-1 leading-relaxed">{analysis.module_purpose}</p>
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
        <div className="bg-white border border-slate-200 rounded-sm p-4 shadow-sm">
          <p className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Summary</p>
          <p className="text-sm text-slate-600 leading-relaxed">{analysis.summary}</p>
        </div>
      )}

      {/* Key Components */}
      {analysis.key_components?.length > 0 && (
        <div className="bg-white border border-slate-200 rounded-sm p-4 shadow-sm">
          <p className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">Key Components</p>
          <div className="flex flex-wrap gap-2">
            {analysis.key_components.map((c, i) => (
              <span key={i} className="text-xs bg-orange-50 border border-orange-200 text-orange-700 px-2 py-1 rounded-sm font-mono">
                {c}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Module Files */}
      {moduleResults.related_files?.length > 0 && (
        <div className="bg-white border border-slate-200 rounded-sm shadow-sm">
          <button
            className="w-full text-left px-4 py-3 flex items-center justify-between"
            onClick={() => setFilesOpen(o => !o)}
          >
            <span className="text-sm font-semibold text-slate-700">
              📂 Module Files <span className="text-slate-400 font-normal">({moduleResults.related_files.length})</span>
            </span>
            <span className="text-slate-400 text-xs">{filesOpen ? '▲' : '▼'}</span>
          </button>
          {filesOpen && (
            <div className="px-4 pb-4 space-y-1 border-t border-slate-100">
              {moduleResults.related_files.map((f, i) => (
                <code key={i} className="block text-xs text-slate-600 bg-slate-50 border border-slate-200 px-2 py-1 mt-1 rounded-sm font-mono">
                  {f}
                </code>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Cross-references */}
      {Object.keys(moduleResults.usage_in_files ?? {}).length > 0 && (
        <div className="bg-white border border-slate-200 rounded-sm shadow-sm">
          <button
            className="w-full text-left px-4 py-3 flex items-center justify-between"
            onClick={() => setUsagesOpen(o => !o)}
          >
            <span className="text-sm font-semibold text-slate-700">
              🔗 Cross-References <span className="text-slate-400 font-normal">({Object.keys(moduleResults.usage_in_files).length} file(s))</span>
            </span>
            <span className="text-slate-400 text-xs">{usagesOpen ? '▲' : '▼'}</span>
          </button>
          {usagesOpen && (
            <div className="px-4 pb-4 space-y-3 border-t border-slate-100">
              {Object.entries(moduleResults.usage_in_files).map(([path, hits]) => (
                <div key={path} className="mt-3">
                  <code className="text-xs text-orange-600 font-mono font-semibold">{path}</code>
                  {hits.map((h, i) => (
                    <code key={i} className="block text-xs text-slate-500 mt-1 bg-slate-50 border border-slate-200 px-2 py-1 rounded-sm font-mono">
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
          <p className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">Module Issues ({analysis.issues.length})</p>
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
        <div className="bg-green-50 border border-green-200 rounded-sm p-4 flex items-start gap-2">
          <span className="text-lg">✅</span>
          <p className="text-sm text-green-700 leading-relaxed">{analysis.summary}</p>
        </div>
      ) : null}
    </div>
  )
}
