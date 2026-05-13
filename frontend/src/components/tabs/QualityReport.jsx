import { useState } from 'react'

function ScoreBadge({ score }) {
  const s = Number(score) || 0
  const color = s >= 80 ? 'text-green-600' : s >= 60 ? 'text-amber-600' : 'text-red-600'
  const ring = s >= 80 ? 'border-green-400' : s >= 60 ? 'border-amber-400' : 'border-red-400'
  const bg = s >= 80 ? 'bg-green-50' : s >= 60 ? 'bg-amber-50' : 'bg-red-50'
  return (
    <div className={`inline-flex flex-col items-center justify-center w-32 h-32 border-2 ${ring} ${bg} rounded-sm`}>
      <span className={`text-5xl font-bold ${color}`}>{Math.round(s)}</span>
      <span className="text-xs text-slate-500 mt-1">/ 100</span>
    </div>
  )
}

function GateDecision({ score }) {
  const s = Number(score) || 0
  const [deployed, setDeployed] = useState(false)

  if (s >= 80) {
    return (
      <div className="bg-green-50 border border-green-300 p-4 rounded-sm">
        <p className="text-green-700 font-semibold text-base">Quality Gate Passed</p>
        <p className="text-green-600 text-sm mt-1">Code is ready for deployment.</p>
        {!deployed ? (
          <button
            onClick={() => setDeployed(true)}
            className="mt-3 px-4 py-1.5 bg-green-600 hover:bg-green-700 text-white text-sm transition-colors uppercase tracking-wide font-semibold rounded-sm"
          >
            Deploy to Production
          </button>
        ) : (
          <p className="mt-3 text-sm text-green-700 font-medium">Deployment pipeline triggered!</p>
        )}
      </div>
    )
  }
  if (s >= 60) {
    return (
      <div className="bg-amber-50 border border-amber-300 p-4 rounded-sm">
        <p className="text-amber-700 font-semibold text-base">Quality Gate Warning</p>
        <p className="text-amber-600 text-sm mt-1">Minor improvements recommended before deployment.</p>
      </div>
    )
  }
  return (
    <div className="bg-red-50 border border-red-300 p-4 rounded-sm">
      <p className="text-red-700 font-semibold text-base">Quality Gate Failed</p>
      <p className="text-red-600 text-sm mt-1">Major fixes required before deployment.</p>
    </div>
  )
}

export default function QualityReport({ results, historyResults }) {
  if (!results) return null
  const score = results.score ?? 0
  const changes = historyResults?.feature_changes ?? []
  const losses = changes.filter(c => c.status?.toLowerCase().includes('loss'))
  const replacements = changes.filter(c =>
    ['replacement', 'refactor', 'updated'].some(w => c.status?.toLowerCase().includes(w))
  )
  const metadata = historyResults?.analysis_metadata ?? {}
  const baseH = String(metadata.base_commit ?? 'initial').slice(0, 8)
  const headH = String(metadata.head_commit ?? 'now').slice(0, 8)

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-8 bg-white border border-slate-200 p-5 rounded-sm shadow-sm">
        <ScoreBadge score={score} />
        <div className="flex-1">
          <p className="text-slate-600 text-sm leading-relaxed">{results.summary}</p>
          <div className="flex gap-4 mt-4">
            <Metric label="Compliance Score" value={`${Math.round(score)}/100`} />
            <Metric label="Issues Found" value={results.issues?.length ?? 0} />
          </div>
        </div>
      </div>

      <GateDecision score={score} />

      {historyResults && !historyResults.error && (
        <div className="bg-white border border-slate-200 p-4 rounded-sm shadow-sm">
          <p className="text-sm font-semibold text-slate-700 mb-3">
            Feature Evolution Summary
            <span className="text-slate-400 ml-2 font-normal text-xs font-mono">
              {baseH} → {headH}
            </span>
          </p>
          <div className="grid grid-cols-2 gap-3">
            <div className={`p-3 text-center rounded-sm ${losses.length ? 'bg-red-50 border border-red-200' : 'bg-green-50 border border-green-200'}`}>
              <p className={`text-xl font-bold ${losses.length ? 'text-red-600' : 'text-green-600'}`}>
                {losses.length}
              </p>
              <p className="text-xs text-slate-500 mt-0.5">Feature Loss{losses.length !== 1 ? 'es' : ''}</p>
            </div>
            <div className="p-3 text-center bg-amber-50 border border-amber-200 rounded-sm">
              <p className="text-xl font-bold text-amber-600">{replacements.length}</p>
              <p className="text-xs text-slate-500 mt-0.5">Replacement{replacements.length !== 1 ? 's' : ''}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function Metric({ label, value }) {
  return (
    <div className="bg-slate-50 border border-slate-200 px-4 py-2.5 min-w-28 rounded-sm">
      <p className="text-xs text-slate-500">{label}</p>
      <p className="text-lg font-semibold text-slate-900 mt-0.5">{value}</p>
    </div>
  )
}
