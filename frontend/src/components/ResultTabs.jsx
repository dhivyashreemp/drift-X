import { useState } from 'react'
import QualityReport from './tabs/QualityReport'
import Issues from './tabs/Issues'
import FeatureEvolution from './tabs/FeatureEvolution'
import ModuleAnalysis from './tabs/ModuleAnalysis'
import History from './tabs/History'
import CodeIssues from './tabs/CodeIssues'

export default function ResultTabs({ results, historyResults, moduleResults, codeLevelResults, repoUrl, jobId, onDownloadPDF, pdfDownloading, pdfError }) {
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
      <div className="bg-zinc-900 border border-zinc-800 rounded-t-sm shadow-sm overflow-hidden">
        <div className="flex items-center overflow-x-auto border-b border-zinc-800">
          {tabs.map(t => (
            <button
              key={t.id}
              onClick={() => setActive(t.id)}
              className={`px-5 py-3.5 text-sm font-semibold whitespace-nowrap border-b-2 transition-all flex items-center gap-2 ${
                active === t.id
                  ? 'border-neon-500 text-neon-500 bg-neon-500/5'
                  : 'border-transparent text-zinc-500 hover:text-zinc-200 hover:bg-zinc-800/50'
              }`}
            >
              <span className="text-xs">{t.icon}</span>
              {t.label}
              {t.badge > 0 && (
                <span className="bg-red-900/60 text-red-400 text-[10px] px-1.5 py-0.5 rounded-full font-bold min-w-[18px] text-center border border-red-700/50">
                  {t.badge}
                </span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Tab content */}
      <div className="bg-zinc-900 border-x border-zinc-800 px-6 py-6">
        {active === 'quality' && <QualityReport results={results} historyResults={historyResults} codeLevelResults={codeLevelResults} />}
        {active === 'issues' && <Issues issues={results?.issues || []} />}
        {active === 'evolution' && <FeatureEvolution historyResults={historyResults} />}
        {active === 'code' && <CodeIssues codeLevelResults={codeLevelResults} />}
        {active === 'module' && moduleResults && <ModuleAnalysis moduleResults={moduleResults} />}
        {active === 'history' && <History repoUrl={repoUrl} historyResults={historyResults} />}
      </div>

      {/* Footer bar */}
      <div className="bg-zinc-900/80 border border-zinc-800 border-t-0 rounded-b-sm px-6 py-4 flex items-center justify-between shadow-sm">
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-2 h-2 rounded-full bg-neon-500 shrink-0" />
          <p className="text-sm text-zinc-400 font-medium">Analysis complete</p>
          <div className="h-4 w-px bg-zinc-700" />
          <p className="text-xs text-zinc-500">
            Job ID: <code className="text-zinc-400 font-mono bg-zinc-800 px-1.5 py-0.5 rounded">{jobId?.slice(0, 8)}</code>
          </p>
          {pdfError && (
            <p className="text-xs text-red-400 font-medium truncate max-w-xs">PDF error: {pdfError}</p>
          )}
        </div>
        <button
          onClick={onDownloadPDF}
          disabled={pdfDownloading}
          className="flex items-center gap-2.5 px-5 py-2.5 bg-neon-500 hover:bg-neon-600 active:bg-neon-500/80 disabled:opacity-60 disabled:cursor-not-allowed text-zinc-900 text-sm font-bold transition-colors uppercase tracking-widest rounded-sm shadow-sm shrink-0"
        >
          {pdfDownloading ? (
            <>
              <span className="animate-spin inline-block h-4 w-4 border-2 border-zinc-900 border-t-transparent rounded-full" />
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
