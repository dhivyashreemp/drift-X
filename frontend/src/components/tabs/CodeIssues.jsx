import { useState } from 'react'

const SEV_ORDER = { Critical: 0, High: 1, Medium: 2, Low: 3 }

const SEV_STYLES = {
  Critical: { badge: 'bg-red-100 text-red-700 border-red-300', dot: 'bg-red-500', icon: '🔴' },
  High:     { badge: 'bg-orange-100 text-orange-700 border-orange-300', dot: 'bg-orange-500', icon: '🟠' },
  Medium:   { badge: 'bg-amber-100 text-amber-700 border-amber-200', dot: 'bg-amber-400', icon: '🟡' },
  Low:      { badge: 'bg-slate-100 text-slate-600 border-slate-300', dot: 'bg-slate-400', icon: '🔵' },
}

const CATEGORY_META = {
  auth:           { label: 'Auth & Authorization', icon: '🔐', color: 'text-rose-600 bg-rose-50 border-rose-200' },
  pipeline:       { label: 'Pipeline & Concurrency', icon: '⚙️', color: 'text-orange-600 bg-orange-50 border-orange-200' },
  dependencies:   { label: 'Dependencies', icon: '📦', color: 'text-indigo-600 bg-indigo-50 border-indigo-200' },
  complexity:     { label: 'Complexity', icon: '🔀', color: 'text-purple-600 bg-purple-50 border-purple-200' },
  security:       { label: 'Security (Bandit)', icon: '🛡️', color: 'text-red-600 bg-red-50 border-red-200' },
  error_handling: { label: 'Error Handling', icon: '⚠️', color: 'text-yellow-700 bg-yellow-50 border-yellow-200' },
  observability:  { label: 'Observability', icon: '📡', color: 'text-blue-600 bg-blue-50 border-blue-200' },
  dead_code:      { label: 'Dead Code', icon: '💀', color: 'text-slate-600 bg-slate-50 border-slate-200' },
}

function renderBlocks(text) {
  if (!text) return null
  const parts = text.split(/(```[\w]*\n[\s\S]*?```)/g)
  return parts.map((part, i) => {
    const m = part.match(/^```(\w*)\n([\s\S]*?)```$/)
    if (m) {
      return (
        <pre key={i} className="bg-slate-900 text-slate-100 text-xs rounded p-3 overflow-x-auto my-2 leading-relaxed">
          <code>{m[2]}</code>
        </pre>
      )
    }
    if (!part.trim()) return null
    return <span key={i} className="whitespace-pre-wrap">{part}</span>
  })
}

function IssueRow({ issue }) {
  const [open, setOpen] = useState(false)
  const sev = issue.severity || 'Low'
  const styles = SEV_STYLES[sev] || SEV_STYLES.Low
  const catMeta = CATEGORY_META[issue.category] || { label: issue.category, icon: '📋', color: 'text-slate-600 bg-slate-50 border-slate-200' }

  return (
    <div className="border border-slate-200 rounded-sm bg-white shadow-sm">
      <button
        className="w-full text-left px-4 py-3 flex items-start gap-3 hover:bg-slate-50 transition-colors"
        onClick={() => setOpen(o => !o)}
      >
        <span className="text-sm shrink-0 mt-0.5">{styles.icon}</span>
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-1.5 mb-1">
            <span className={`text-[11px] px-1.5 py-0.5 font-bold border rounded-sm ${styles.badge}`}>{sev}</span>
            <span className={`text-[11px] px-1.5 py-0.5 font-semibold border rounded-sm ${catMeta.color}`}>
              {catMeta.icon} {issue.subcategory || catMeta.label}
            </span>
            <span className="text-[11px] text-slate-400 font-mono truncate max-w-[280px]">
              {issue.file}{issue.line ? `:${issue.line}` : ''}
            </span>
          </div>
          <p className="text-sm text-slate-700 leading-snug line-clamp-2">{issue.description}</p>
        </div>
        <span className="text-slate-400 text-xs shrink-0 mt-1">{open ? '▲' : '▼'}</span>
      </button>

      {open && (
        <div className="border-t border-slate-100 divide-y divide-slate-100">
          <div className="px-4 py-3">
            <p className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-1.5">📋 What's wrong</p>
            <p className="text-sm text-slate-700 leading-relaxed">{issue.description}</p>
          </div>
          {issue.evidence && (
            <div className="px-4 py-3">
              <p className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-1.5">📍 Where in code</p>
              <div className="text-sm text-slate-700 leading-relaxed">{renderBlocks(issue.evidence)}</div>
            </div>
          )}
          {issue.remediation && (
            <div className="px-4 py-3 bg-blue-50">
              <p className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-1.5">🔧 How to fix</p>
              <div className="text-sm text-blue-800 leading-relaxed">{renderBlocks(issue.remediation)}</div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function FileGroup({ filePath, issues }) {
  const [open, setOpen] = useState(false)
  const critCount = issues.filter(i => i.severity === 'Critical').length
  const highCount = issues.filter(i => i.severity === 'High').length

  return (
    <div className="border border-slate-200 rounded-sm bg-white shadow-sm">
      <button
        className="w-full text-left px-4 py-3 flex items-center gap-3 hover:bg-slate-50 transition-colors"
        onClick={() => setOpen(o => !o)}
      >
        <span className="text-sm">📄</span>
        <span className="flex-1 text-sm font-mono text-slate-700 truncate">{filePath}</span>
        <div className="flex items-center gap-2 shrink-0">
          {critCount > 0 && (
            <span className="text-[11px] bg-red-100 text-red-700 border border-red-300 px-1.5 py-0.5 rounded-sm font-bold">
              ●{critCount} Critical
            </span>
          )}
          {highCount > 0 && (
            <span className="text-[11px] bg-orange-100 text-orange-700 border border-orange-200 px-1.5 py-0.5 rounded-sm font-bold">
              ●{highCount} High
            </span>
          )}
          <span className="text-[11px] text-slate-400">{issues.length} issue{issues.length !== 1 ? 's' : ''}</span>
          <span className="text-slate-400 text-xs">{open ? '▲' : '▼'}</span>
        </div>
      </button>
      {open && (
        <div className="border-t border-slate-100 divide-y divide-slate-100">
          {issues.map((issue, i) => (
            <IssueRow key={i} issue={issue} />
          ))}
        </div>
      )}
    </div>
  )
}

const CATEGORY_KEYS = ['auth', 'pipeline', 'dependencies', 'security', 'error_handling', 'complexity', 'observability', 'dead_code']

function buildAllIssues(codeLevelResults) {
  const all = []

  // Static analysis issues (already have category field)
  const byCategory = codeLevelResults?.by_category || {}
  for (const [cat, issues] of Object.entries(byCategory)) {
    for (const issue of issues) {
      all.push({ ...issue, source: 'static' })
    }
  }

  // LLM analysis issues — map to unified structure
  const llmMap = {
    auth_issues:           'auth',
    pipeline_issues:       'pipeline',
    dependency_issues:     'dependencies',
    error_handling_issues: 'error_handling',
    observability_issues:  'observability',
  }
  for (const [key, cat] of Object.entries(llmMap)) {
    for (const issue of (codeLevelResults?.[`llm_${key}`] || codeLevelResults?.[key] || [])) {
      all.push({ ...issue, category: issue.category || cat, source: 'llm' })
    }
  }

  return all
}

const VIEWS = [
  { key: 'by_category', label: 'By Category' },
  { key: 'by_file', label: 'By File' },
  { key: 'flat', label: 'Flat List' },
]

export default function CodeIssues({ codeLevelResults }) {
  const [activeCategory, setActiveCategory] = useState('all')
  const [activeView, setActiveView] = useState('by_category')

  if (!codeLevelResults) {
    return (
      <div className="flex flex-col items-center justify-center h-48 text-slate-400 bg-white border border-slate-200 rounded-sm">
        <p className="text-3xl mb-2">🔍</p>
        <p className="font-medium">No code-level analysis available</p>
        <p className="text-xs mt-1">Re-run the analysis to generate this report</p>
      </div>
    )
  }

  const allIssues = buildAllIssues(codeLevelResults)

  if (allIssues.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-48 text-slate-400 bg-white border border-slate-200 rounded-sm">
        <p className="text-3xl mb-2">✅</p>
        <p className="font-medium">No code-level issues detected</p>
      </div>
    )
  }

  // Build category counts
  const categoryCounts = {}
  for (const issue of allIssues) {
    categoryCounts[issue.category] = (categoryCounts[issue.category] || 0) + 1
  }

  const filteredIssues = activeCategory === 'all'
    ? allIssues
    : allIssues.filter(i => i.category === activeCategory)

  const sortedIssues = [...filteredIssues].sort((a, b) =>
    (SEV_ORDER[a.severity] ?? 9) - (SEV_ORDER[b.severity] ?? 9)
  )

  // Group by file for by_file view
  const byFile = {}
  for (const issue of sortedIssues) {
    byFile[issue.file] = [...(byFile[issue.file] || []), issue]
  }

  // Group by category for by_category view
  const byCategory = {}
  for (const issue of sortedIssues) {
    byCategory[issue.category] = [...(byCategory[issue.category] || []), issue]
  }

  const severityCounts = { Critical: 0, High: 0, Medium: 0, Low: 0 }
  for (const issue of allIssues) {
    severityCounts[issue.severity] = (severityCounts[issue.severity] || 0) + 1
  }

  return (
    <div className="space-y-4">
      {/* LLM Summary */}
      {codeLevelResults.summary && (
        <div className="bg-amber-50 border border-amber-200 rounded-sm px-4 py-3">
          <p className="text-xs font-bold text-amber-700 uppercase tracking-wider mb-1">Analysis Summary</p>
          <p className="text-sm text-amber-900 leading-relaxed">{codeLevelResults.summary}</p>
        </div>
      )}

      {/* Severity overview */}
      <div className="grid grid-cols-4 gap-2">
        {Object.entries(severityCounts).map(([sev, n]) => (
          <div key={sev} className={`border rounded-sm p-2.5 text-center ${SEV_STYLES[sev]?.badge || ''}`}>
            <p className="text-lg font-bold">{n}</p>
            <p className="text-xs mt-0.5">{sev}</p>
          </div>
        ))}
      </div>

      {/* Category filter */}
      <div className="flex flex-wrap gap-1.5">
        <button
          onClick={() => setActiveCategory('all')}
          className={`text-xs px-3 py-1.5 font-semibold rounded-sm border transition-all ${
            activeCategory === 'all'
              ? 'bg-orange-500 text-white border-orange-500 shadow-sm'
              : 'bg-white text-slate-600 border-slate-300 hover:text-slate-900'
          }`}
        >
          All ({allIssues.length})
        </button>
        {CATEGORY_KEYS.filter(k => categoryCounts[k] > 0).map(cat => {
          const meta = CATEGORY_META[cat] || { label: cat, icon: '📋' }
          return (
            <button
              key={cat}
              onClick={() => setActiveCategory(cat)}
              className={`text-xs px-3 py-1.5 font-semibold rounded-sm border transition-all flex items-center gap-1 ${
                activeCategory === cat
                  ? 'bg-orange-500 text-white border-orange-500 shadow-sm'
                  : 'bg-white text-slate-600 border-slate-300 hover:text-slate-900'
              }`}
            >
              {meta.icon} {meta.label} ({categoryCounts[cat]})
            </button>
          )
        })}
      </div>

      {/* View toggle */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-500">
          Showing <span className="font-semibold">{filteredIssues.length}</span> issue{filteredIssues.length !== 1 ? 's' : ''}
          {activeCategory !== 'all' && <span className="ml-1 text-slate-400">in {CATEGORY_META[activeCategory]?.label || activeCategory}</span>}
        </p>
        <div className="flex gap-1">
          {VIEWS.map(v => (
            <button
              key={v.key}
              onClick={() => setActiveView(v.key)}
              className={`text-xs px-3 py-1 font-semibold uppercase tracking-wide rounded-sm transition-all border ${
                activeView === v.key
                  ? 'bg-orange-500 text-white border-orange-500'
                  : 'bg-white text-slate-500 border-slate-300 hover:text-slate-800'
              }`}
            >
              {v.label}
            </button>
          ))}
        </div>
      </div>

      {/* Issue list */}
      <div className="space-y-2">
        {activeView === 'flat' && sortedIssues.map((issue, i) => (
          <IssueRow key={i} issue={issue} />
        ))}

        {activeView === 'by_file' && Object.entries(byFile)
          .sort(([, a], [, b]) => {
            const aMax = Math.min(...a.map(i => SEV_ORDER[i.severity] ?? 9))
            const bMax = Math.min(...b.map(i => SEV_ORDER[i.severity] ?? 9))
            return aMax - bMax || b.length - a.length
          })
          .map(([filePath, issues]) => (
            <FileGroup key={filePath} filePath={filePath} issues={issues} />
          ))
        }

        {activeView === 'by_category' && CATEGORY_KEYS
          .filter(cat => byCategory[cat]?.length > 0)
          .map(cat => {
            const meta = CATEGORY_META[cat] || { label: cat, icon: '📋', color: 'text-slate-600 bg-slate-50 border-slate-200' }
            const issues = byCategory[cat]
            return (
              <CategoryGroup key={cat} cat={cat} meta={meta} issues={issues} />
            )
          })
        }
      </div>
    </div>
  )
}

function CategoryGroup({ cat, meta, issues }) {
  const [open, setOpen] = useState(true)
  const critCount = issues.filter(i => i.severity === 'Critical').length
  const highCount = issues.filter(i => i.severity === 'High').length

  return (
    <div className="border border-slate-200 rounded-sm overflow-hidden shadow-sm">
      <button
        className={`w-full text-left px-4 py-3 flex items-center gap-3 ${meta.color} transition-colors`}
        onClick={() => setOpen(o => !o)}
      >
        <span className="text-base">{meta.icon}</span>
        <span className="flex-1 text-sm font-bold">{meta.label}</span>
        <div className="flex items-center gap-2 shrink-0">
          {critCount > 0 && (
            <span className="text-[11px] bg-red-100 text-red-700 border border-red-300 px-1.5 py-0.5 rounded-sm font-bold">
              {critCount} Critical
            </span>
          )}
          {highCount > 0 && (
            <span className="text-[11px] bg-orange-100 text-orange-700 border border-orange-200 px-1.5 py-0.5 rounded-sm font-bold">
              {highCount} High
            </span>
          )}
          <span className="text-xs opacity-70">{issues.length} issue{issues.length !== 1 ? 's' : ''}</span>
          <span className="text-xs opacity-70">{open ? '▲' : '▼'}</span>
        </div>
      </button>
      {open && (
        <div className="divide-y divide-slate-100 bg-white">
          {issues.map((issue, i) => (
            <IssueRow key={i} issue={issue} />
          ))}
        </div>
      )}
    </div>
  )
}
