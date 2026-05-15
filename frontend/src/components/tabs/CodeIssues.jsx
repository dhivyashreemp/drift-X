import { useState } from 'react'

const SEV_ORDER = { Critical: 0, High: 1, Medium: 2, Low: 3 }

const SEV_STYLES = {
  Critical: { badge: 'bg-red-900/60 text-red-400 border-red-700/60', dot: 'bg-red-500', icon: '🔴' },
  High:     { badge: 'bg-orange-900/60 text-orange-400 border-orange-700/60', dot: 'bg-orange-500', icon: '🟠' },
  Medium:   { badge: 'bg-amber-900/60 text-amber-400 border-amber-700/60', dot: 'bg-amber-400', icon: '🟡' },
  Low:      { badge: 'bg-zinc-700/60 text-zinc-400 border-zinc-600/60', dot: 'bg-zinc-400', icon: '🔵' },
}

const CATEGORY_META = {
  auth:           { label: 'Auth & Authorization', icon: '🔐', color: 'text-rose-400 bg-rose-950/30 border-rose-700/50' },
  pipeline:       { label: 'Pipeline & Concurrency', icon: '⚙️', color: 'text-orange-400 bg-orange-950/30 border-orange-700/50' },
  dependencies:   { label: 'Dependencies', icon: '📦', color: 'text-indigo-400 bg-indigo-950/30 border-indigo-700/50' },
  complexity:     { label: 'Complexity', icon: '🔀', color: 'text-purple-400 bg-purple-950/30 border-purple-700/50' },
  security:       { label: 'Security (Bandit)', icon: '🛡️', color: 'text-red-400 bg-red-950/30 border-red-700/50' },
  error_handling: { label: 'Error Handling', icon: '⚠️', color: 'text-yellow-400 bg-yellow-950/30 border-yellow-700/50' },
  observability:  { label: 'Observability', icon: '📡', color: 'text-blue-400 bg-blue-950/30 border-blue-700/50' },
  dead_code:      { label: 'Dead Code', icon: '💀', color: 'text-zinc-400 bg-zinc-800/60 border-zinc-700' },
}

const CATEGORY_WEIGHTS = {
  auth: 25, security: 25, pipeline: 20, error_handling: 15,
  dependencies: 8, complexity: 4, observability: 2, dead_code: 1,
}

function renderBlocks(text) {
  if (!text) return null
  const parts = text.split(/(```[\w]*\n[\s\S]*?```)/g)
  return parts.map((part, i) => {
    const m = part.match(/^```(\w*)\n([\s\S]*?)```$/)
    if (m) {
      return (
        <pre key={i} className="bg-zinc-950 text-zinc-200 text-xs rounded p-3 overflow-x-auto my-2 leading-relaxed border border-zinc-800">
          <code>{m[2]}</code>
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
    return <p className="text-sm text-zinc-300 leading-relaxed">{trimmed}</p>
  }
  const lines = trimmed.split('\n').filter(l => l.trim())
  return (
    <ul className="space-y-1.5">
      {lines.map((line, i) => {
        const clean = line.startsWith('- ') ? line.slice(2) : line
        return (
          <li key={i} className="flex items-start gap-2 text-sm text-zinc-300 leading-relaxed">
            <span className="text-neon-500 shrink-0 font-bold mt-0.5">•</span>
            <span>{clean}</span>
          </li>
        )
      })}
    </ul>
  )
}

function ScoreRing({ score }) {
  const s = Number(score) || 0
  const color = s >= 85 ? 'text-green-400' : s >= 65 ? 'text-amber-400' : 'text-red-400'
  const ringColor = s >= 85 ? 'border-green-600' : s >= 65 ? 'border-amber-600' : 'border-red-600'
  const bg = s >= 85 ? 'bg-green-950/30' : s >= 65 ? 'bg-amber-950/30' : 'bg-red-950/30'
  return (
    <div className={`flex flex-col items-center justify-center w-24 h-24 border-4 ${ringColor} ${bg} rounded-full`}>
      <span className={`text-3xl font-black ${color}`}>{Math.round(s)}</span>
      <span className="text-[10px] text-zinc-500 font-medium">/ 100</span>
    </div>
  )
}

function CategoryScoreBar({ cat, score }) {
  const s = Number(score) || 0
  const color = s >= 85 ? 'bg-green-500' : s >= 65 ? 'bg-amber-500' : 'bg-red-500'
  const textColor = s >= 85 ? 'text-green-400' : s >= 65 ? 'text-amber-400' : 'text-red-400'
  const meta = CATEGORY_META[cat] || { label: cat }
  return (
    <div className="flex items-center gap-3">
      <span className="text-xs text-zinc-400 w-36 shrink-0 truncate">{meta.label}</span>
      <div className="flex-1 bg-zinc-700 h-2 rounded-full">
        <div className={`${color} h-2 rounded-full transition-all`} style={{ width: `${s}%` }} />
      </div>
      <span className={`text-xs font-bold w-8 text-right tabular-nums ${textColor}`}>{s}</span>
      <span className="text-[10px] text-zinc-600 w-10 text-right">{CATEGORY_WEIGHTS[cat] ? `${CATEGORY_WEIGHTS[cat]}%` : ''}</span>
    </div>
  )
}

function IssueRow({ issue }) {
  const [open, setOpen] = useState(false)
  const sev = issue.severity || 'Low'
  const styles = SEV_STYLES[sev] || SEV_STYLES.Low
  const catMeta = CATEGORY_META[issue.category] || { label: issue.category, icon: '📋', color: 'text-zinc-400 bg-zinc-800/60 border-zinc-700' }

  return (
    <div className="border border-zinc-700 rounded-sm bg-zinc-800/50 shadow-sm">
      <button
        className="w-full text-left px-4 py-3 flex items-start gap-3 hover:bg-zinc-700/30 transition-colors"
        onClick={() => setOpen(o => !o)}
      >
        <span className="text-sm shrink-0 mt-0.5">{styles.icon}</span>
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-1.5 mb-1">
            <span className={`text-[11px] px-1.5 py-0.5 font-bold border rounded-sm ${styles.badge}`}>{sev}</span>
            <span className={`text-[11px] px-1.5 py-0.5 font-semibold border rounded-sm ${catMeta.color}`}>
              {catMeta.icon} {issue.subcategory || catMeta.label}
            </span>
            <span className="text-[11px] text-zinc-500 font-mono truncate max-w-[280px]">
              {issue.file}{issue.line ? `:${issue.line}` : ''}
            </span>
          </div>
          <p className="text-sm text-zinc-300 leading-snug line-clamp-2">{issue.description}</p>
        </div>
        <span className="text-zinc-600 text-xs shrink-0 mt-1">{open ? '▲' : '▼'}</span>
      </button>

      {open && (
        <div className="border-t border-zinc-700 divide-y divide-zinc-800">
          <div className="px-4 py-3">
            <p className="text-xs font-bold text-zinc-500 uppercase tracking-wider mb-1.5">📋 What's wrong</p>
            <p className="text-sm text-zinc-300 leading-relaxed">{issue.description}</p>
          </div>
          {issue.evidence && (
            <div className="px-4 py-3">
              <p className="text-xs font-bold text-zinc-500 uppercase tracking-wider mb-1.5">📍 Where in code</p>
              <div className="text-sm text-zinc-300 leading-relaxed">{renderBlocks(issue.evidence)}</div>
            </div>
          )}
          {issue.remediation && (
            <div className="px-4 py-3 bg-neon-500/5">
              <p className="text-xs font-bold text-zinc-500 uppercase tracking-wider mb-1.5">🔧 Recommended Fix</p>
              <div className="text-sm text-neon-400 leading-relaxed">{renderBlocks(issue.remediation)}</div>
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
    <div className="border border-zinc-700 rounded-sm bg-zinc-800/50 shadow-sm">
      <button
        className="w-full text-left px-4 py-3 flex items-center gap-3 hover:bg-zinc-700/30 transition-colors"
        onClick={() => setOpen(o => !o)}
      >
        <span className="text-sm">📄</span>
        <span className="flex-1 text-sm font-mono text-zinc-300 truncate">{filePath}</span>
        <div className="flex items-center gap-2 shrink-0">
          {critCount > 0 && (
            <span className="text-[11px] bg-red-900/60 text-red-400 border border-red-700/50 px-1.5 py-0.5 rounded-sm font-bold">
              ●{critCount} Critical
            </span>
          )}
          {highCount > 0 && (
            <span className="text-[11px] bg-orange-900/60 text-orange-400 border border-orange-700/50 px-1.5 py-0.5 rounded-sm font-bold">
              ●{highCount} High
            </span>
          )}
          <span className="text-[11px] text-zinc-500">{issues.length} issue{issues.length !== 1 ? 's' : ''}</span>
          <span className="text-zinc-600 text-xs">{open ? '▲' : '▼'}</span>
        </div>
      </button>
      {open && (
        <div className="border-t border-zinc-700 divide-y divide-zinc-800">
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

  const byCategory = codeLevelResults?.by_category || {}
  for (const [cat, issues] of Object.entries(byCategory)) {
    for (const issue of issues) {
      all.push({ ...issue, source: 'static' })
    }
  }

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
  const [scoringOpen, setScoringOpen] = useState(false)

  if (!codeLevelResults) {
    return (
      <div className="flex flex-col items-center justify-center h-48 text-zinc-500 bg-zinc-800 border border-zinc-700 rounded-sm">
        <p className="text-3xl mb-2">🔍</p>
        <p className="font-medium text-zinc-300">No code-level analysis available</p>
        <p className="text-xs mt-1">Re-run the analysis to generate this report</p>
      </div>
    )
  }

  const allIssues = buildAllIssues(codeLevelResults)
  const codeScore = codeLevelResults.code_level_score
  const categoryScores = codeLevelResults.category_scores || {}

  if (allIssues.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-48 text-zinc-500 bg-zinc-800 border border-zinc-700 rounded-sm">
        <p className="text-3xl mb-2">✅</p>
        <p className="font-medium text-zinc-300">No code-level issues detected</p>
      </div>
    )
  }

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

  const byFile = {}
  for (const issue of sortedIssues) {
    byFile[issue.file] = [...(byFile[issue.file] || []), issue]
  }

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
      {/* Score + Summary row */}
      <div className="bg-zinc-800 border border-zinc-700 rounded-sm p-4 shadow-sm">
        <div className="flex items-start gap-5">
          {codeScore != null && <ScoreRing score={codeScore} />}
          <div className="flex-1 min-w-0">
            {codeLevelResults.summary && (
              <>
                <p className="text-xs font-bold text-zinc-500 uppercase tracking-wider mb-2">Analysis Summary</p>
                {renderBullets(codeLevelResults.summary)}
              </>
            )}
            {!codeLevelResults.summary && (
              <p className="text-sm text-zinc-500">Static analysis complete. {allIssues.length} issues found.</p>
            )}
          </div>
        </div>
      </div>

      {/* Category scores + scoring methodology */}
      {Object.keys(categoryScores).length > 0 && (
        <div className="bg-zinc-800 border border-zinc-700 rounded-sm shadow-sm overflow-hidden">
          <button
            className="w-full text-left px-4 py-3 flex items-center justify-between hover:bg-zinc-700/30 transition-colors"
            onClick={() => setScoringOpen(o => !o)}
          >
            <span className="text-xs font-bold text-zinc-400 uppercase tracking-wider">Category Scores &amp; Scoring Methodology</span>
            <span className="text-zinc-500 text-xs">{scoringOpen ? '▲' : '▼'}</span>
          </button>
          {scoringOpen && (
            <div className="px-4 pb-4 border-t border-zinc-700">
              <div className="mt-3 space-y-2.5">
                {Object.entries(categoryScores)
                  .sort(([a], [b]) => (CATEGORY_WEIGHTS[b] || 0) - (CATEGORY_WEIGHTS[a] || 0))
                  .map(([cat, s]) => (
                    <CategoryScoreBar key={cat} cat={cat} score={s} />
                  ))}
              </div>
              <div className="mt-4 bg-zinc-900/50 border border-zinc-700 rounded-sm p-3">
                <p className="text-xs font-bold text-zinc-400 uppercase tracking-wider mb-2">How scoring works</p>
                <ul className="space-y-1 text-xs text-zinc-400">
                  <li><span className="text-neon-500">•</span> Each category starts at <strong className="text-zinc-200">100 points</strong></li>
                  <li><span className="text-neon-500">•</span> Deductions per issue: <strong className="text-red-400">Critical −15</strong> · <strong className="text-orange-400">High −8</strong> · <strong className="text-amber-400">Medium −3</strong> · <strong className="text-zinc-300">Low −1</strong></li>
                  <li><span className="text-neon-500">•</span> Per-severity deductions are capped: Critical max −45, High max −24, Medium max −12, Low max −5</li>
                  <li><span className="text-neon-500">•</span> Overall code score is a <strong className="text-zinc-200">weighted average</strong> of all category scores</li>
                  <li><span className="text-neon-500">•</span> Weights reflect business risk: Auth 25% · Security 25% · Pipeline 20% · Error Handling 15% · Dependencies 8% · Complexity 4% · Observability 2% · Dead Code 1%</li>
                </ul>
              </div>
            </div>
          )}
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
              ? 'bg-neon-500 text-zinc-900 border-neon-500 shadow-sm'
              : 'bg-zinc-800 text-zinc-400 border-zinc-700 hover:text-zinc-200'
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
                  ? 'bg-neon-500 text-zinc-900 border-neon-500 shadow-sm'
                  : 'bg-zinc-800 text-zinc-400 border-zinc-700 hover:text-zinc-200'
              }`}
            >
              {meta.icon} {meta.label} ({categoryCounts[cat]})
            </button>
          )
        })}
      </div>

      {/* View toggle */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-zinc-500">
          Showing <span className="font-semibold text-zinc-200">{filteredIssues.length}</span> issue{filteredIssues.length !== 1 ? 's' : ''}
          {activeCategory !== 'all' && <span className="ml-1 text-zinc-600">in {CATEGORY_META[activeCategory]?.label || activeCategory}</span>}
        </p>
        <div className="flex gap-1">
          {VIEWS.map(v => (
            <button
              key={v.key}
              onClick={() => setActiveView(v.key)}
              className={`text-xs px-3 py-1 font-semibold uppercase tracking-wide rounded-sm transition-all border ${
                activeView === v.key
                  ? 'bg-neon-500 text-zinc-900 border-neon-500'
                  : 'bg-zinc-800 text-zinc-500 border-zinc-700 hover:text-zinc-200'
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
            const meta = CATEGORY_META[cat] || { label: cat, icon: '📋', color: 'text-zinc-400 bg-zinc-800/60 border-zinc-700' }
            const issues = byCategory[cat]
            return (
              <CategoryGroup key={cat} cat={cat} meta={meta} issues={issues} catScore={categoryScores[cat]} />
            )
          })
        }
      </div>
    </div>
  )
}

function CategoryGroup({ cat, meta, issues, catScore }) {
  const [open, setOpen] = useState(true)
  const critCount = issues.filter(i => i.severity === 'Critical').length
  const highCount = issues.filter(i => i.severity === 'High').length
  const s = Number(catScore) || null
  const scoreColor = s == null ? '' : s >= 85 ? 'text-green-400' : s >= 65 ? 'text-amber-400' : 'text-red-400'

  return (
    <div className="border border-zinc-700 rounded-sm overflow-hidden shadow-sm">
      <button
        className={`w-full text-left px-4 py-3 flex items-center gap-3 ${meta.color} transition-colors`}
        onClick={() => setOpen(o => !o)}
      >
        <span className="text-base">{meta.icon}</span>
        <span className="flex-1 text-sm font-bold">{meta.label}</span>
        <div className="flex items-center gap-2 shrink-0">
          {s != null && (
            <span className={`text-xs font-bold ${scoreColor}`}>{s}/100</span>
          )}
          {critCount > 0 && (
            <span className="text-[11px] bg-red-900/60 text-red-400 border border-red-700/50 px-1.5 py-0.5 rounded-sm font-bold">
              {critCount} Critical
            </span>
          )}
          {highCount > 0 && (
            <span className="text-[11px] bg-orange-900/60 text-orange-400 border border-orange-700/50 px-1.5 py-0.5 rounded-sm font-bold">
              {highCount} High
            </span>
          )}
          <span className="text-xs opacity-70">{issues.length} issue{issues.length !== 1 ? 's' : ''}</span>
          <span className="text-xs opacity-70">{open ? '▲' : '▼'}</span>
        </div>
      </button>
      {open && (
        <div className="divide-y divide-zinc-800 bg-zinc-900/50">
          {issues.map((issue, i) => (
            <IssueRow key={i} issue={issue} />
          ))}
        </div>
      )}
    </div>
  )
}
