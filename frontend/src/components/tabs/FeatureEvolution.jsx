import { useState } from 'react'

const SEVERITY_STYLES = {
  Critical: 'text-red-600 font-semibold',
  High: 'text-orange-600 font-semibold',
  Medium: 'text-amber-600',
  Low: 'text-slate-500',
}

function statusStyle(status = '') {
  const s = status.toLowerCase()
  if (s.includes('loss')) return 'bg-red-100 text-red-700 border-red-300'
  if (s.includes('replacement') || s.includes('refactor')) return 'bg-amber-100 text-amber-700 border-amber-300'
  if (s.includes('updated')) return 'bg-blue-100 text-blue-700 border-blue-300'
  return 'bg-slate-100 text-slate-600 border-slate-300'
}

function StatusBadge({ status }) {
  return (
    <span className={`text-xs px-2 py-0.5 border font-semibold rounded-sm ${statusStyle(status)}`}>
      {status}
    </span>
  )
}

function ChangeCard({ change }) {
  const [open, setOpen] = useState(false)
  const isLoss = change.status?.toLowerCase().includes('loss')

  return (
    <div className={`border rounded-sm shadow-sm ${isLoss ? 'border-red-200 bg-red-50' : 'border-slate-200 bg-white'}`}>
      <button
        className="w-full text-left px-4 py-3 flex items-start gap-3"
        onClick={() => setOpen(o => !o)}
      >
        <span className="text-sm mt-0.5">{isLoss ? '❌' : '🔄'}</span>
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-semibold text-sm text-slate-800">{change.feature_name}</span>
            <StatusBadge status={change.status} />
            {change.severity && (
              <span className={`text-xs ${SEVERITY_STYLES[change.severity] || 'text-slate-500'}`}>
                {change.severity}
              </span>
            )}
          </div>
          {change.impact && (
            <p className="text-xs text-slate-500 mt-1 line-clamp-1">{change.impact}</p>
          )}
        </div>
        <span className="text-slate-400 shrink-0">{open ? '▲' : '▼'}</span>
      </button>

      {open && (
        <div className="px-4 pb-4 space-y-3 border-t border-slate-200 pt-3">
          {change.impact && <Field label="Impact" value={change.impact} />}
          {change.reasoning && <Field label="Reasoning" value={change.reasoning} />}
          {change.replacement_logic && (
            <div className="bg-amber-50 border border-amber-200 p-3 rounded-sm">
              <p className="text-xs text-amber-700 mb-1 font-semibold uppercase tracking-wide">Replacement Logic</p>
              <p className="text-sm text-amber-800 leading-relaxed">{change.replacement_logic}</p>
            </div>
          )}
          {change.evidence && (
            <div>
              <p className="text-xs text-slate-500 mb-1 font-semibold uppercase tracking-wide">Evidence</p>
              <code className="text-xs text-slate-700 bg-slate-100 border border-slate-200 px-2 py-1.5 block rounded-sm whitespace-pre-wrap">{change.evidence}</code>
            </div>
          )}
          {change.remediation && (
            <div className="bg-blue-50 border border-blue-200 p-3 rounded-sm">
              <p className="text-xs text-blue-700 mb-1 font-semibold uppercase tracking-wide">Recommended Fix</p>
              <p className="text-sm text-blue-800 leading-relaxed">{change.remediation}</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function Field({ label, value }) {
  return (
    <div>
      <p className="text-xs text-slate-500 mb-1 font-semibold uppercase tracking-wide">{label}</p>
      <p className="text-sm text-slate-600 leading-relaxed">{value}</p>
    </div>
  )
}

export default function FeatureEvolution({ historyResults }) {
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

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <p className="text-sm text-slate-600">
          {changes.length} change{changes.length !== 1 ? 's' : ''} detected
        </p>
        {(metadata.base_commit || metadata.head_commit) && (
          <span className="text-xs text-slate-500 font-mono bg-slate-100 border border-slate-200 px-2 py-1 rounded-sm">
            {String(metadata.base_commit ?? '').slice(0, 8)} → {String(metadata.head_commit ?? '').slice(0, 8)}
          </span>
        )}
      </div>

      {historyResults.summary && (
        <div className="bg-white border border-slate-200 p-4 rounded-sm shadow-sm">
          <p className="text-xs text-slate-500 mb-1 font-semibold uppercase tracking-wide">Summary</p>
          <p className="text-sm text-slate-700 leading-relaxed">{historyResults.summary}</p>
        </div>
      )}

      <div className="space-y-2">
        {changes.map((c, i) => (
          <ChangeCard key={i} change={c} />
        ))}
      </div>
    </div>
  )
}
