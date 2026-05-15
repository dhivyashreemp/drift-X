import { useState } from 'react'

const VERDICT_CONFIG = {
  APPROVED:    { bg: 'bg-green-950/40',  border: 'border-green-700', text: 'text-green-400',  label: 'Approved for Deployment', sub: 'Code meets quality standards and is ready to ship.', icon: '✅' },
  CONDITIONAL: { bg: 'bg-amber-950/40',  border: 'border-amber-700', text: 'text-amber-400',  label: 'Conditional — Fix Before Release', sub: 'Issues found that must be resolved before the next release.', icon: '⚠️' },
  BLOCKED:     { bg: 'bg-red-950/40',    border: 'border-red-700',   text: 'text-red-400',    label: 'Blocked — Do Not Deploy', sub: 'Critical issues detected. Deployment must not proceed.', icon: '🚫' },
}

function getVerdict(score, explicitVerdict) {
  if (explicitVerdict && VERDICT_CONFIG[explicitVerdict]) return explicitVerdict
  if (score >= 85) return 'APPROVED'
  if (score >= 65) return 'CONDITIONAL'
  return 'BLOCKED'
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

function ScoreRing({ score, label, size = 'lg' }) {
  const s = Number(score) || 0
  const color = s >= 85 ? 'text-green-400' : s >= 65 ? 'text-amber-400' : 'text-red-400'
  const ringColor = s >= 85 ? 'border-green-600' : s >= 65 ? 'border-amber-600' : 'border-red-600'
  const bg = s >= 85 ? 'bg-green-950/30' : s >= 65 ? 'bg-amber-950/30' : 'bg-red-950/30'
  const sizeClasses = size === 'sm'
    ? 'w-20 h-20 border-4'
    : 'w-28 h-28 border-4'
  const numClasses = size === 'sm' ? 'text-2xl' : 'text-4xl'
  return (
    <div className={`flex flex-col items-center justify-center ${sizeClasses} ${ringColor} ${bg} rounded-full shrink-0`}>
      <span className={`${numClasses} font-black ${color}`}>{Math.round(s)}</span>
      <span className="text-[10px] text-zinc-500 font-medium">{label || '/ 100'}</span>
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
          className="px-5 py-2 bg-green-700 hover:bg-green-600 text-white text-sm font-bold uppercase tracking-wide rounded-sm transition-colors shrink-0"
        >
          Deploy to Production
        </button>
      )}
      {verdict === 'APPROVED' && deployed && (
        <span className="text-sm text-green-400 font-semibold shrink-0">Pipeline triggered!</span>
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
    <div className="bg-zinc-800 border border-zinc-700 rounded-sm p-4 shadow-sm">
      <p className="text-xs font-bold text-zinc-400 uppercase tracking-wider mb-3">Issues by Category</p>
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
        {sorted.map(([cat, count]) => (
          <div key={cat} className="flex items-center gap-2 bg-zinc-700/50 border border-zinc-700 rounded-sm px-3 py-2">
            <span className="text-base shrink-0">{CATEGORY_ICONS[cat] || '❓'}</span>
            <div className="min-w-0">
              <p className="text-xs text-zinc-400 leading-tight truncate">{cat}</p>
              <p className="text-sm font-bold text-zinc-100">{count}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

const CATEGORY_WEIGHTS = {
  auth: 25, security: 25, pipeline: 20, error_handling: 15,
  dependencies: 8, complexity: 4, observability: 2, dead_code: 1,
}
const CATEGORY_LABELS = {
  auth: 'Auth & Access Control', security: 'Security', pipeline: 'Pipeline & Concurrency',
  error_handling: 'Error Handling', dependencies: 'Dependencies', complexity: 'Complexity',
  observability: 'Observability', dead_code: 'Dead Code',
}

function CategoryScoreBar({ cat, score }) {
  const s = Number(score) || 0
  const color = s >= 85 ? 'bg-green-500' : s >= 65 ? 'bg-amber-500' : 'bg-red-500'
  const textColor = s >= 85 ? 'text-green-400' : s >= 65 ? 'text-amber-400' : 'text-red-400'
  return (
    <div className="flex items-center gap-3">
      <span className="text-xs text-zinc-400 w-36 shrink-0 truncate">{CATEGORY_LABELS[cat] || cat}</span>
      <div className="flex-1 bg-zinc-700 h-2 rounded-full">
        <div className={`${color} h-2 rounded-full transition-all`} style={{ width: `${s}%` }} />
      </div>
      <span className={`text-xs font-bold w-8 text-right tabular-nums ${textColor}`}>{s}</span>
      <span className="text-[10px] text-zinc-600 w-10 text-right">{CATEGORY_WEIGHTS[cat] ? `${CATEGORY_WEIGHTS[cat]}%` : ''}</span>
    </div>
  )
}

export default function QualityReport({ results, historyResults, codeLevelResults }) {
  const [deployed, setDeployed] = useState(false)
  const [scoringOpen, setScoringOpen] = useState(false)

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

  const codeScore = codeLevelResults?.code_level_score
  const categoryScores = codeLevelResults?.category_scores || {}
  const hasCategoryScores = Object.keys(categoryScores).length > 0

  return (
    <div className="space-y-5">
      {/* Score + Summary row */}
      <div className="flex items-start gap-6 bg-zinc-800 border border-zinc-700 rounded-sm p-5 shadow-sm">
        <div className="flex flex-col items-center gap-3 shrink-0">
          <ScoreRing score={score} label="Quality" />
          {codeScore != null && (
            <div className="text-center">
              <p className="text-[10px] text-zinc-500 uppercase tracking-wider mb-1">Code Level</p>
              <ScoreRing score={codeScore} label="Code" size="sm" />
            </div>
          )}
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-xs font-bold text-zinc-500 uppercase tracking-wider mb-2">Overall Summary</p>
          {renderBullets(results.summary)}
          <div className="flex flex-wrap gap-3 mt-4">
            <Metric label="Quality Score" value={`${Math.round(score)} / 100`} />
            {codeScore != null && <Metric label="Code Level Score" value={`${codeScore} / 100`} warn={codeScore < 85} crit={codeScore < 65} />}
            <Metric label="Issues Found" value={issueCount} warn={issueCount > 0} />
            <Metric label="Evolution Problems" value={netEvolutionProblems.length} warn={netEvolutionProblems.length > 0} />
            <Metric label="Total Problems" value={totalIssues} crit={totalIssues > 0} />
          </div>
        </div>
      </div>

      {/* Code Level Category Scores */}
      {hasCategoryScores && (
        <div className="bg-zinc-800 border border-zinc-700 rounded-sm shadow-sm overflow-hidden">
          <button
            className="w-full text-left px-4 py-3 flex items-center justify-between hover:bg-zinc-700/30 transition-colors"
            onClick={() => setScoringOpen(o => !o)}
          >
            <span className="text-xs font-bold text-zinc-400 uppercase tracking-wider">Code Level Category Scores</span>
            <span className="text-zinc-500 text-xs">{scoringOpen ? '▲' : '▼'}</span>
          </button>
          {scoringOpen && (
            <div className="px-4 pb-4 space-y-3 border-t border-zinc-700">
              <p className="text-[10px] text-zinc-500 mt-3 leading-relaxed">
                Each category starts at 100. Deductions: Critical −15 (cap 45), High −8 (cap 24), Medium −3 (cap 12), Low −1 (cap 5).
                Overall code score is a weighted average: Auth 25% · Security 25% · Pipeline 20% · Error Handling 15% · Dependencies 8% · Complexity 4% · Observability 2% · Dead Code 1%.
              </p>
              <div className="space-y-2.5 mt-2">
                {Object.entries(categoryScores)
                  .sort(([a], [b]) => (CATEGORY_WEIGHTS[b] || 0) - (CATEGORY_WEIGHTS[a] || 0))
                  .map(([cat, s]) => (
                    <CategoryScoreBar key={cat} cat={cat} score={s} />
                  ))}
              </div>
            </div>
          )}
        </div>
      )}

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
        <div className="bg-zinc-800 border border-zinc-700 rounded-sm p-4 shadow-sm">
          <p className="text-xs font-bold text-zinc-400 uppercase tracking-wider mb-3">Feature Evolution</p>
          <div className="grid grid-cols-3 gap-3">
            <EvolutionMetric label="Feature Losses / Regressions" value={losses.length} danger={losses.length > 0} />
            <EvolutionMetric label="Replacements / Refactors" value={replacements.length} />
            <EvolutionMetric label="Total Changes Tracked" value={changes.length} />
          </div>
          {historyResults.summary && (
            <div className="border-t border-zinc-700 pt-3 mt-3">
              {renderBullets(historyResults.summary)}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function Metric({ label, value, warn, crit }) {
  const color = crit ? 'text-red-400' : warn ? 'text-amber-400' : 'text-zinc-100'
  const bg = crit ? 'bg-red-950/30 border-red-700/50' : warn ? 'bg-amber-950/30 border-amber-700/50' : 'bg-zinc-700/50 border-zinc-700'
  return (
    <div className={`px-4 py-2.5 min-w-28 rounded-sm border ${bg}`}>
      <p className="text-xs text-zinc-500">{label}</p>
      <p className={`text-lg font-bold mt-0.5 ${color}`}>{value}</p>
    </div>
  )
}

function EvolutionMetric({ label, value, danger }) {
  return (
    <div className={`p-3 text-center rounded-sm border ${danger && value > 0 ? 'bg-red-950/30 border-red-700/50' : 'bg-zinc-700/50 border-zinc-700'}`}>
      <p className={`text-xl font-bold ${danger && value > 0 ? 'text-red-400' : 'text-zinc-200'}`}>{value}</p>
      <p className="text-xs text-zinc-500 mt-0.5 leading-tight">{label}</p>
    </div>
  )
}
