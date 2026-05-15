import { useState } from 'react'
import QualityReport from './tabs/QualityReport'
import Issues from './tabs/Issues'
import FeatureEvolution from './tabs/FeatureEvolution'
import ModuleAnalysis from './tabs/ModuleAnalysis'
import History from './tabs/History'
import CodeIssues from './tabs/CodeIssues'

export default function ResultTabs({ results, historyResults, moduleResults, codeLevelResults, repoUrl, jobId, onDownloadPDF, pdfDownloading, pdfError }) {
  // Only count actual problems — exclude replacements/refactors/preserved changes
  const evolutionCount = (historyResults?.feature_changes ?? []).filter(c =>
    !['replacement', 'refactor', 'updated', 'preserved'].some(w =>
      (c.status || '').toLowerCase().includes(w)
    )
  ).length

  const codeLevelCount = codeLevelResults?.total_static_issues || 0

  const tabs = [
    { id: 'quality', label: 'Quality Report', icon: '📊' },
    { id: 'issues', label: 'Issues', icon: '⚡', badge: results?.issues?.length },
    { id: 'evolution', label: 'Feature Evolution', icon: '📈', badge: evolutionCount },
    { id: 'code', label: 'Code Level Issues', icon: '🔬', badge: codeLevelCount },
    ...(moduleResults ? [{ id: 'module', label: 'Module', icon: '🧩' }] : []),
    { id: 'history', label: 'History', icon: '🕒' },
  ]

  const [active, setActive] = useState('quality')

  return (
    <div className="space-y-0">
      {/* Tab bar */}
      <div className="bg-white border border-slate-200 rounded-t-sm shadow-sm overflow-hidden">
        <div className="flex items-center overflow-x-auto border-b border-slate-200">
          {tabs.map(t => (
            <button
              key={t.id}
              onClick={() => setActive(t.id)}
              className={`px-5 py-3.5 text-sm font-semibold whitespace-nowrap border-b-2 transition-all flex items-center gap-2 ${
                active === t.id
                  ? 'border-orange-500 text-orange-600 bg-orange-50/60'
                  : 'border-transparent text-slate-500 hover:text-slate-800 hover:bg-slate-50'
              }`}
            >
              <span className="text-xs">{t.icon}</span>
              {t.label}
              {t.badge > 0 && (
                <span className="bg-red-100 text-red-700 text-[10px] px-1.5 py-0.5 rounded-full font-bold min-w-[18px] text-center">
                  {t.badge}
                </span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Tab content */}
      <div className="bg-white border-x border-slate-200 px-6 py-6">
        {active === 'quality' && <QualityReport results={results} historyResults={historyResults} />}
        {active === 'issues' && <Issues issues={results?.issues || []} />}
        {active === 'evolution' && <FeatureEvolution historyResults={historyResults} />}
        {active === 'code' && <CodeIssues codeLevelResults={codeLevelResults} />}
        {active === 'module' && moduleResults && <ModuleAnalysis moduleResults={moduleResults} />}
        {active === 'history' && <History repoUrl={repoUrl} historyResults={historyResults} />}
      </div>

      {/* Footer bar */}
      <div className="bg-slate-50 border border-slate-200 border-t-0 rounded-b-sm px-6 py-4 flex items-center justify-between shadow-sm">
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-2 h-2 rounded-full bg-green-500 shrink-0" />
          <p className="text-sm text-slate-600 font-medium">Analysis complete</p>
          <div className="h-4 w-px bg-slate-300" />
          <p className="text-xs text-slate-400">
            Job ID: <code className="text-slate-500 font-mono bg-slate-100 px-1.5 py-0.5 rounded">{jobId?.slice(0, 8)}</code>
          </p>
          {pdfError && (
            <p className="text-xs text-red-600 font-medium truncate max-w-xs">PDF error: {pdfError}</p>
          )}
        </div>
        <button
          onClick={onDownloadPDF}
          disabled={pdfDownloading}
          className="flex items-center gap-2.5 px-5 py-2.5 bg-orange-500 hover:bg-orange-600 active:bg-orange-700 disabled:opacity-60 disabled:cursor-not-allowed text-white text-sm font-bold transition-colors uppercase tracking-widest rounded-sm shadow-sm shrink-0"
        >
          {pdfDownloading ? (
            <>
              <span className="animate-spin inline-block h-4 w-4 border-2 border-white border-t-transparent rounded-full" />
              Generating...
            </>
          ) : (
            'Download PDF Report'
          )}
        </button>
      </div>
    </div>
  )
}
