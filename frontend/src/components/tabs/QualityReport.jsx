import { useState } from 'react'

const VERDICT_CONFIG = {
  APPROVED:    { bg: 'bg-green-50',  border: 'border-green-400', text: 'text-green-700',  label: 'Approved for Deployment', sub: 'Code meets quality standards and is ready to ship.', icon: '✅' },
  CONDITIONAL: { bg: 'bg-amber-50',  border: 'border-amber-400', text: 'text-amber-700',  label: 'Conditional — Fix Before Release', sub: 'Issues found that must be resolved before the next release.', icon: '⚠️' },
  BLOCKED:     { bg: 'bg-red-50',    border: 'border-red-400',   text: 'text-red-700',    label: 'Blocked — Do Not Deploy', sub: 'Critical issues detected. Deployment must not proceed.', icon: '🚫' },
}

function getVerdict(score, explicitVerdict) {
  if (explicitVerdict && VERDICT_CONFIG[explicitVerdict]) return explicitVerdict
  if (score >= 85) return 'APPROVED'
  if (score >= 65) return 'CONDITIONAL'
  return 'BLOCKED'
}

function ScoreRing({ score }) {
  const s = Number(score) || 0
  const color = s >= 85 ? 'text-green-600' : s >= 65 ? 'text-amber-600' : 'text-red-600'
  const ringColor = s >= 85 ? 'border-green-400' : s >= 65 ? 'border-amber-400' : 'border-red-400'
  const bg = s >= 85 ? 'bg-green-50' : s >= 65 ? 'bg-amber-50' : 'bg-red-50'
  return (
    <div className={`flex flex-col items-center justify-center w-28 h-28 border-4 ${ringColor} ${bg} rounded-full shrink-0`}>
      <span className={`text-4xl font-black ${color}`}>{Math.round(s)}</span>
      <span className="text-xs text-slate-500 font-medium">/ 100</span>
    </div>
  )
}

function VerdictBanner({ score, explicitVerdict, deployed, onDeploy }) {
  const verdict = getVerdict(score, explicitVerdict)
  const cfg = VERDICT_CONFIG[verdict]
  return (
    <div className={`${cfg.bg} border-2 ${cfg.border} rounded-sm p-4 flex items-center gap-4`}>
      <span className="text-3xl">{cfg.icon}</span>
      <div className="flex-1">
        <p className={`font-bold text-base ${cfg.text}`}>{cfg.label}</p>
        <p className={`text-sm mt-0.5 ${cfg.text} opacity-80`}>{cfg.sub}</p>
      </div>
      {verdict === 'APPROVED' && !deployed && (
        <button
          onClick={onDeploy}
          className="px-5 py-2 bg-green-600 hover:bg-green-700 text-white text-sm font-bold uppercase tracking-wide rounded-sm transition-colors shrink-0"
        >
          Deploy to Production
        </button>
      )}
      {verdict === 'APPROVED' && deployed && (
        <span className="text-sm text-green-700 font-semibold shrink-0">Pipeline triggered!</span>
      )}
    </div>
  )
}

function IssueBreakdown({ issues }) {
  if (!issues?.length) return null

  const groups = {}
  issues.forEach(issue => {
    const cat = issue.type || 'Other'
    groups[cat] = (groups[cat] || 0) + 1
  })

  const CATEGORY_ICONS = {
    'Security Vulnerability': '🔒',
    'Requirement Drift':      '📐',
    'Feature Completeness':   '🧩',
    'Code Quality':           '🔍',
    'Error Handling':         '⚡',
    'Testing Gap':            '🧪',
    'Guideline Violation':    '📋',
    'Performance Issue':      '🚀',
    'Deployment Readiness':   '🚢',
    'Observability Gap':      '👁️',
    'Dependency Risk':        '📦',
  }

  const CATEGORY_PRIORITY = [
    'Security Vulnerability', 'Requirement Drift', 'Feature Completeness',
    'Error Handling', 'Testing Gap', 'Performance Issue', 'Deployment Readiness',
    'Observability Gap', 'Code Quality', 'Guideline Violation', 'Dependency Risk',
  ]

  const sorted = Object.entries(groups).sort(
    ([a], [b]) => (CATEGORY_PRIORITY.indexOf(a) + 1 || 99) - (CATEGORY_PRIORITY.indexOf(b) + 1 || 99)
  )

  return (
    <div className="bg-white border border-slate-200 rounded-sm p-4 shadow-sm">
      <p className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">Issues by Category</p>
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
        {sorted.map(([cat, count]) => (
          <div key={cat} className="flex items-center gap-2 bg-slate-50 border border-slate-200 rounded-sm px-3 py-2">
            <span className="text-base shrink-0">{CATEGORY_ICONS[cat] || '❓'}</span>
            <div className="min-w-0">
              <p className="text-xs text-slate-500 leading-tight truncate">{cat}</p>
              <p className="text-sm font-bold text-slate-800">{count}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default function QualityReport({ results, historyResults }) {
  const [deployed, setDeployed] = useState(false)

  if (!results) return null

  const score = results.score ?? 0
  const changes = historyResults?.feature_changes ?? []
  const losses = changes.filter(c => c.status?.toLowerCase().includes('loss') || c.status?.toLowerCase().includes('regression') || c.status?.toLowerCase().includes('missing'))
  const replacements = changes.filter(c =>
    ['replacement', 'refactor', 'updated', 'preserved'].some(w => c.status?.toLowerCase().includes(w))
  )
  const issueCount = results.issues?.length ?? 0

  const isReplacement = c => ['replacement', 'refactor', 'updated', 'preserved'].some(w => (c.status || '').toLowerCase().includes(w))
  const isAlreadyCounted = c => c.status === 'Loss' && c.severity === 'Critical'
  const netEvolutionProblems = changes.filter(c => !isReplacement(c) && !isAlreadyCounted(c))
  const totalIssues = issueCount + netEvolutionProblems.length

  return (
    <div className="space-y-5">
      {/* Score + Summary row */}
      <div className="flex items-center gap-6 bg-white border border-slate-200 rounded-sm p-5 shadow-sm">
        <ScoreRing score={score} />
        <div className="flex-1 min-w-0">
          <p className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-1">Overall Summary</p>
          <p className="text-sm text-slate-600 leading-relaxed">{results.summary}</p>
          <div className="flex flex-wrap gap-3 mt-4">
            <Metric label="Quality Score" value={`${Math.round(score)} / 100`} />
            <Metric label="Issues Found" value={issueCount} warn={issueCount > 0} />
            <Metric label="Evolution Problems" value={netEvolutionProblems.length} warn={netEvolutionProblems.length > 0} />
            <Metric label="Total Problems" value={totalIssues} crit={totalIssues > 0} />
          </div>
        </div>
      </div>

      {/* Deployment Verdict */}
      <VerdictBanner
        score={score}
        explicitVerdict={results.deployment_verdict}
        deployed={deployed}
        onDeploy={() => setDeployed(true)}
      />

      {/* Issue category breakdown */}
      <IssueBreakdown issues={results.issues} />

      {/* Feature evolution summary */}
      {historyResults && !historyResults.error && (
        <div className="bg-white border border-slate-200 rounded-sm p-4 shadow-sm">
          <p className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">Feature Evolution</p>
          <div className="grid grid-cols-3 gap-3">
            <EvolutionMetric label="Feature Losses / Regressions" value={losses.length} danger={losses.length > 0} />
            <EvolutionMetric label="Replacements / Refactors" value={replacements.length} />
            <EvolutionMetric label="Total Changes Tracked" value={changes.length} />
          </div>
          {historyResults.summary && (
            <p className="text-xs text-slate-500 mt-3 leading-relaxed border-t border-slate-100 pt-3">
              {historyResults.summary}
            </p>
          )}
        </div>
      )}
    </div>
  )
}

function Metric({ label, value, warn, crit }) {
  const color = crit ? 'text-red-700' : warn ? 'text-amber-700' : 'text-slate-900'
  const bg = crit ? 'bg-red-50 border-red-200' : warn ? 'bg-amber-50 border-amber-200' : 'bg-slate-50 border-slate-200'
  return (
    <div className={`px-4 py-2.5 min-w-28 rounded-sm border ${bg}`}>
      <p className="text-xs text-slate-500">{label}</p>
      <p className={`text-lg font-bold mt-0.5 ${color}`}>{value}</p>
    </div>
  )
}

function EvolutionMetric({ label, value, danger }) {
  return (
    <div className={`p-3 text-center rounded-sm border ${danger && value > 0 ? 'bg-red-50 border-red-200' : 'bg-slate-50 border-slate-200'}`}>
      <p className={`text-xl font-bold ${danger && value > 0 ? 'text-red-600' : 'text-slate-700'}`}>{value}</p>
      <p className="text-xs text-slate-500 mt-0.5 leading-tight">{label}</p>
    </div>
  )
}
