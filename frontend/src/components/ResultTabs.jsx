import { useState } from 'react'
import QualityReport from './tabs/QualityReport'
import Issues from './tabs/Issues'
import FeatureEvolution from './tabs/FeatureEvolution'
import ModuleAnalysis from './tabs/ModuleAnalysis'
import History from './tabs/History'

export default function ResultTabs({ results, historyResults, moduleResults, repoUrl, jobId, onDownloadPDF }) {
  const tabs = [
    { id: 'quality', label: '📊 Quality Report' },
    { id: 'issues', label: '🚨 Issues', badge: results?.issues?.length },
    { id: 'evolution', label: '🧬 Evolution' },
    ...(moduleResults ? [{ id: 'module', label: '🔍 Module' }] : []),
    { id: 'history', label: '📜 History' },
  ]

  const [active, setActive] = useState('quality')

  return (
    <div>
      {/* Tab bar */}
      <div className="flex items-center gap-1 border-b border-navy-700 mb-6 overflow-x-auto">
        {tabs.map(t => (
          <button
            key={t.id}
            onClick={() => setActive(t.id)}
            className={`px-4 py-2.5 text-sm font-medium whitespace-nowrap border-b-2 transition-all flex items-center gap-1.5 ${
              active === t.id
                ? 'border-orange-500 text-orange-400'
                : 'border-transparent text-slate-500 hover:text-slate-300'
            }`}
          >
            {t.label}
            {t.badge > 0 && (
              <span className="bg-red-900 text-red-300 text-xs px-1.5 py-0.5">
                {t.badge}
              </span>
            )}
          </button>
        ))}
      </div>

      <div>
        {active === 'quality' && <QualityReport results={results} historyResults={historyResults} />}
        {active === 'issues' && <Issues issues={results?.issues || []} />}
        {active === 'evolution' && <FeatureEvolution historyResults={historyResults} />}
        {active === 'module' && moduleResults && <ModuleAnalysis moduleResults={moduleResults} />}
        {active === 'history' && <History repoUrl={repoUrl} historyResults={historyResults} />}
      </div>

      <div className="mt-8 pt-6 border-t border-navy-700 flex items-center justify-between">
        <p className="text-sm text-slate-500">
          Analysis complete — job <code className="text-slate-600 text-xs">{jobId?.slice(0, 8)}</code>
        </p>
        <button
          onClick={onDownloadPDF}
          className="flex items-center gap-2 px-4 py-2 bg-orange-500 hover:bg-orange-600 text-white text-sm font-semibold transition-colors uppercase tracking-wide"
        >
          ⬇ Download PDF Report
        </button>
      </div>
    </div>
  )
}
