import { useState } from 'react'

const STATUS_STYLES = {
  loss: 'bg-red-900/50 text-red-300 border-red-800',
  replacement: 'bg-orange-900/40 text-orange-300 border-orange-800',
  updated: 'bg-navy-700 text-slate-300 border-navy-600',
  default: 'bg-navy-800 text-slate-300 border-navy-700',
}

const SEVERITY_STYLES = {
  Critical: 'text-red-400',
  High: 'text-orange-400',
  Medium: 'text-amber-400',
  Low: 'text-slate-400',
}

function statusStyle(status = '') {
  const s = status.toLowerCase()
  if (s.includes('loss')) return STATUS_STYLES.loss
  if (s.includes('replacement') || s.includes('refactor')) return STATUS_STYLES.replacement
  if (s.includes('updated')) return STATUS_STYLES.updated
  return STATUS_STYLES.default
}

function StatusBadge({ status }) {
  return (
    <span className={`text-xs px-2 py-0.5 border font-medium ${statusStyle(status)}`}>
      {status}
    </span>
  )
}

function ChangeCard({ change }) {
  const [open, setOpen] = useState(false)
  const isLoss = change.status?.toLowerCase().includes('loss')

  return (
    <div className={`border ${isLoss ? 'border-red-900 bg-red-950/20' : 'border-navy-700 bg-navy-900'}`}>
      <button
        className="w-full text-left px-4 py-3 flex items-start gap-3"
        onClick={() => setOpen(o => !o)}
      >
        <span className="text-sm mt-0.5">{isLoss ? '❌' : '🔄'}</span>
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-medium text-sm text-slate-200">{change.feature_name}</span>
            <StatusBadge status={change.status} />
            {change.severity && (
              <span className={`text-xs font-medium ${SEVERITY_STYLES[change.severity] || 'text-slate-400'}`}>
                {change.severity}
              </span>
            )}
          </div>
          {change.impact && (
            <p className="text-xs text-slate-500 mt-1 line-clamp-1">{change.impact}</p>
          )}
        </div>
        <span className="text-slate-600 shrink-0">{open ? '▲' : '▼'}</span>
      </button>

      {open && (
        <div className="px-4 pb-4 space-y-3 border-t border-navy-700/50 pt-3">
          {change.impact && <Field label="Impact" value={change.impact} />}
          {change.reasoning && <Field label="Reasoning" value={change.reasoning} />}
          {change.replacement_logic && (
            <div className="bg-orange-950/20 border border-orange-900/40 p-3">
              <p className="text-xs text-orange-400 mb-1 font-semibold">🔄 Replacement Logic</p>
              <p className="text-sm text-orange-300/80">{change.replacement_logic}</p>
            </div>
          )}
          {change.evidence && (
            <div>
              <p className="text-xs text-slate-500 mb-1 font-medium">Evidence</p>
              <code className="text-xs text-slate-400 bg-navy-800 px-2 py-1.5 block">{change.evidence}</code>
            </div>
          )}
          {change.remediation && (
            <div className="bg-orange-950/20 border border-orange-900/50 p-3">
              <p className="text-xs text-orange-400 mb-1 font-semibold">🤖 AI Remediation</p>
              <p className="text-sm text-orange-300/80">{change.remediation}</p>
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
      <p className="text-xs text-slate-500 mb-1 font-medium">{label}</p>
      <p className="text-sm text-slate-400">{value}</p>
    </div>
  )
}

export default function FeatureEvolution({ historyResults }) {
  if (!historyResults || historyResults.error) {
    return (
      <div className="text-slate-600 text-center py-12">
        No feature evolution data available.
      </div>
    )
  }

  const changes = historyResults.feature_changes ?? []
  const metadata = historyResults.analysis_metadata ?? {}

  if (changes.length === 0) {
    return (
      <div className="text-center py-12 text-slate-600">
        <p className="text-2xl mb-2">✅</p>
        <p>No feature changes detected in this commit range.</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <p className="text-sm text-slate-400">
          {changes.length} change{changes.length !== 1 ? 's' : ''} detected
        </p>
        {(metadata.base_commit || metadata.head_commit) && (
          <span className="text-xs text-slate-600 font-mono bg-navy-800 border border-navy-700 px-2 py-1">
            {String(metadata.base_commit ?? '').slice(0, 8)} → {String(metadata.head_commit ?? '').slice(0, 8)}
          </span>
        )}
      </div>

      {historyResults.summary && (
        <div className="bg-navy-900 border border-navy-700 p-4">
          <p className="text-xs text-slate-500 mb-1 font-medium">Summary</p>
          <p className="text-sm text-slate-300">{historyResults.summary}</p>
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
