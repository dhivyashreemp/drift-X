import { useState } from 'react'

function MetricCard({ label, value }) {
  return (
    <div className="bg-navy-800/60 border border-navy-700 p-4 text-center">
      <p className="text-2xl font-bold text-white">{value}</p>
      <p className="text-xs text-slate-500 mt-1">{label}</p>
    </div>
  )
}

function IssueCard({ issue }) {
  const [open, setOpen] = useState(false)
  const critical = ['loss', 'drift', 'violation', 'missing', 'failed'].some(
    w => (issue.type || '').toLowerCase().includes(w)
  )

  return (
    <div className={`border ${critical ? 'border-red-900 bg-red-950/20' : 'border-navy-700 bg-navy-900'}`}>
      <button className="w-full text-left px-4 py-3 flex items-start gap-2" onClick={() => setOpen(o => !o)}>
        <span className="text-sm">{critical ? '🚨' : 'ℹ️'}</span>
        <div className="flex-1">
          <span className="text-xs bg-navy-700 text-slate-300 px-2 py-0.5 border border-navy-600">{issue.type}</span>
          <p className="text-sm text-slate-300 mt-1">{issue.description}</p>
        </div>
        <span className="text-slate-600">{open ? '▲' : '▼'}</span>
      </button>
      {open && (
        <div className="px-4 pb-4 pt-3 border-t border-navy-700/50 space-y-3">
          {issue.evidence && (
            <div>
              <p className="text-xs text-slate-500 mb-1 font-medium">Evidence</p>
              <code className="text-xs text-slate-400 bg-navy-800 px-2 py-1.5 block">{issue.evidence}</code>
            </div>
          )}
          {issue.reasoning && (
            <div>
              <p className="text-xs text-slate-500 mb-1 font-medium">Reasoning</p>
              <p className="text-sm text-slate-400">{issue.reasoning}</p>
            </div>
          )}
          {issue.remediation && (
            <div className="bg-orange-950/20 border border-orange-900/50 p-3">
              <p className="text-xs text-orange-400 mb-1 font-semibold">🤖 Remediation</p>
              <p className="text-sm text-orange-300/80">{issue.remediation}</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default function ModuleAnalysis({ moduleResults }) {
  const [filesOpen, setFilesOpen] = useState(false)
  const [usagesOpen, setUsagesOpen] = useState(false)

  if (!moduleResults) return null

  const analysis = moduleResults.analysis ?? {}
  const modScore = analysis.compliance_score
  const scoreColor = modScore >= 80 ? 'text-green-400' : modScore >= 60 ? 'text-amber-400' : 'text-red-400'

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-white">
          🔍 Module: <span className="text-orange-400">{moduleResults.module_name}</span>
        </h2>
        {analysis.module_purpose && (
          <p className="text-sm text-slate-400 mt-2">{analysis.module_purpose}</p>
        )}
      </div>

      <div className="grid grid-cols-3 gap-3">
        <MetricCard label="Files Found" value={moduleResults.file_count} />
        <MetricCard label="Referenced In" value={`${moduleResults.usage_count} file(s)`} />
        <div className="bg-navy-800/60 border border-navy-700 p-4 text-center">
          <p className={`text-2xl font-bold ${scoreColor}`}>
            {modScore != null ? `${Math.round(modScore)}` : 'N/A'}
          </p>
          <p className="text-xs text-slate-500 mt-1">Module Score</p>
        </div>
      </div>

      {analysis.key_components?.length > 0 && (
        <div className="bg-navy-900 border border-navy-700 p-4">
          <p className="text-sm font-semibold text-slate-300 mb-3">📦 Key Components</p>
          <ul className="space-y-1">
            {analysis.key_components.map((c, i) => (
              <li key={i} className="text-sm text-slate-400 flex items-start gap-2">
                <span className="text-orange-500 mt-0.5">•</span> {c}
              </li>
            ))}
          </ul>
        </div>
      )}

      {moduleResults.related_files?.length > 0 && (
        <div className="bg-navy-900 border border-navy-700">
          <button
            className="w-full text-left px-4 py-3 flex items-center justify-between"
            onClick={() => setFilesOpen(o => !o)}
          >
            <span className="text-sm font-semibold text-slate-300">
              📂 Module Files ({moduleResults.related_files.length})
            </span>
            <span className="text-slate-600">{filesOpen ? '▲' : '▼'}</span>
          </button>
          {filesOpen && (
            <div className="px-4 pb-4 pt-0 space-y-1 border-t border-navy-700">
              {moduleResults.related_files.map((f, i) => (
                <code key={i} className="block text-xs text-slate-400 bg-navy-800 border border-navy-700 px-2 py-1 mt-1">
                  {f}
                </code>
              ))}
            </div>
          )}
        </div>
      )}

      {Object.keys(moduleResults.usage_in_files ?? {}).length > 0 && (
        <div className="bg-navy-900 border border-navy-700">
          <button
            className="w-full text-left px-4 py-3 flex items-center justify-between"
            onClick={() => setUsagesOpen(o => !o)}
          >
            <span className="text-sm font-semibold text-slate-300">
              🔗 Cross-References ({Object.keys(moduleResults.usage_in_files).length} file(s))
            </span>
            <span className="text-slate-600">{usagesOpen ? '▲' : '▼'}</span>
          </button>
          {usagesOpen && (
            <div className="px-4 pb-4 pt-0 space-y-3 border-t border-navy-700">
              {Object.entries(moduleResults.usage_in_files).map(([path, hits]) => (
                <div key={path} className="mt-3">
                  <code className="text-xs text-orange-400">{path}</code>
                  {hits.map((h, i) => (
                    <code key={i} className="block text-xs text-slate-500 mt-1 bg-navy-800 border border-navy-700 px-2 py-1">
                      L{h.line}: {h.content}
                    </code>
                  ))}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {analysis.issues?.length > 0 && (
        <div>
          <p className="text-sm font-semibold text-slate-300 mb-3">Module Issues</p>
          <div className="space-y-2">
            {analysis.issues.map((issue, i) => (
              <IssueCard key={i} issue={issue} />
            ))}
          </div>
        </div>
      )}

      {!analysis.issues?.length && analysis.summary && (
        <div className="bg-green-950/20 border border-green-900 p-4">
          <p className="text-green-400 text-sm">✅ {analysis.summary}</p>
        </div>
      )}
    </div>
  )
}
