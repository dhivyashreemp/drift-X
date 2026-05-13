import { useState, useRef } from 'react'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import LoginPage from './pages/LoginPage'
import NavBar from './components/NavBar'
import Sidebar from './components/Sidebar'
import ResultTabs from './components/ResultTabs'
import TeamDashboard from './components/TeamDashboard'
import MyScoreView from './components/MyScoreView'

const POLL_MS = 3000

const makeRepo = () => ({
  id: crypto.randomUUID(),
  url: '',
  branch: '',
  token: '',
  commits: [],
  headCommit: '',
  baseCommit: '',
  fetchStatus: 'idle',
  fetchError: '',
})

function AnalysisView() {
  const { authFetch } = useAuth()

  const [repos, setRepos] = useState([makeRepo()])
  const [moduleName, setModuleName] = useState('')
  const [requirementsFiles, setRequirementsFiles] = useState([])
  const [dosDontsFiles, setDosDontsFiles] = useState([])

  const [jobId, setJobId] = useState(null)
  const [analysisStatus, setAnalysisStatus] = useState('idle')
  const [progressMessage, setProgressMessage] = useState('')
  const [analysisResult, setAnalysisResult] = useState(null)
  const [isPrivateRepoError, setIsPrivateRepoError] = useState(false)
  const pollRef = useRef(null)

  const updateRepo = (id, patch) =>
    setRepos(prev => prev.map(r => r.id === id ? { ...r, ...patch } : r))

  const addRepo = () => setRepos(prev => [...prev, makeRepo()])

  const removeRepo = (id) =>
    setRepos(prev => prev.length > 1 ? prev.filter(r => r.id !== id) : prev)

  const handleFetchRepo = async (repoId) => {
    const repo = repos.find(r => r.id === repoId)
    if (!repo?.url.trim()) return
    updateRepo(repoId, { fetchStatus: 'loading', fetchError: '', commits: [] })
    try {
      const fd = new FormData()
      fd.append('repo_url', repo.url.trim())
      fd.append('branch', repo.branch.trim())
      fd.append('git_token', repo.token.trim())
      const res = await authFetch('/api/fetch-repo', { method: 'POST', body: fd })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Failed to fetch repository')
      updateRepo(repoId, {
        commits: data.commits,
        headCommit: data.commits[0]?.hash || '',
        baseCommit: data.commits[data.commits.length - 1]?.hash || '',
        fetchStatus: 'success',
        fetchError: '',
      })
    } catch (e) {
      updateRepo(repoId, { fetchError: e.message, fetchStatus: 'error' })
    }
  }

  const startPolling = (id) => {
    clearInterval(pollRef.current)
    pollRef.current = setInterval(async () => {
      try {
        const res = await authFetch(`/api/jobs/${id}`)
        const job = await res.json()
        setProgressMessage(job.progress || '')
        if (job.status === 'complete') {
          clearInterval(pollRef.current)
          setAnalysisResult(job.result)
          setAnalysisStatus('complete')
        } else if (job.status === 'error') {
          clearInterval(pollRef.current)
          setAnalysisStatus('error')
          setProgressMessage(job.error || 'Analysis failed')
          setIsPrivateRepoError(!!job.private_repo)
        }
      } catch (_) {}
    }, POLL_MS)
  }

  const handleStartAnalysis = async () => {
    const activeRepos = repos.filter(r => r.url.trim())
    if (!activeRepos.length || requirementsFiles.length === 0) return

    setAnalysisStatus('running')
    setProgressMessage('Submitting analysis job...')
    setAnalysisResult(null)
    setIsPrivateRepoError(false)

    try {
      const reposData = activeRepos.map(r => ({
        url: r.url.trim(),
        branch: r.branch.trim(),
        token: r.token.trim(),
        base_commit: r.baseCommit,
        head_commit: r.headCommit,
      }))

      const fd = new FormData()
      fd.append('repos_json', JSON.stringify(reposData))
      fd.append('module_name', moduleName.trim())
      requirementsFiles.forEach(f => fd.append('requirements_files', f))
      dosDontsFiles.forEach(f => fd.append('dos_donts_files', f))

      const res = await authFetch('/api/analyze', { method: 'POST', body: fd })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Failed to start analysis')
      setJobId(data.job_id)
      setProgressMessage('Analysis queued...')
      startPolling(data.job_id)
    } catch (e) {
      setAnalysisStatus('error')
      setProgressMessage(e.message)
    }
  }

  const handleDownloadPDF = async () => {
    if (!jobId) return
    const res = await authFetch(`/api/report/${jobId}`, { method: 'POST' })
    if (res.ok) {
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `driftx_report_${Date.now()}.pdf`
      a.click()
      URL.revokeObjectURL(url)
    }
  }

  const canAnalyze = repos.some(r => r.url.trim()) && requirementsFiles.length > 0 && analysisStatus !== 'running'
  const repoCount = repos.filter(r => r.url.trim()).length

  return (
    <div className="flex flex-1 overflow-hidden">
      <Sidebar
        repos={repos}
        onUpdateRepo={updateRepo}
        onFetchRepo={handleFetchRepo}
        onAddRepo={addRepo}
        onRemoveRepo={removeRepo}
        moduleName={moduleName}
        setModuleName={setModuleName}
        requirementsFiles={requirementsFiles}
        setRequirementsFiles={setRequirementsFiles}
        dosDontsFiles={dosDontsFiles}
        setDosDontsFiles={setDosDontsFiles}
        onStartAnalysis={handleStartAnalysis}
        canAnalyze={canAnalyze}
        analysisRunning={analysisStatus === 'running'}
      />

      <main className="flex-1 overflow-y-auto bg-slate-50">
        <div className="p-6 max-w-5xl mx-auto">
          {analysisStatus === 'idle' && !analysisResult && (
            <div className="flex flex-col items-center justify-center h-72 text-slate-400 border border-dashed border-slate-300 bg-white rounded-sm">
              <div className="w-16 h-16 bg-orange-50 border border-orange-200 flex items-center justify-center mb-4 rounded-sm">
                <span className="text-3xl">🛡️</span>
              </div>
              <p className="text-base text-slate-600 font-medium">Configure repositories and run an analysis</p>
              <p className="text-sm text-slate-400 mt-1">Add repo URLs and requirement docs to get started</p>
            </div>
          )}

          {analysisStatus === 'running' && (
            <div className="flex flex-col items-center justify-center h-72 bg-white border border-slate-200">
              <div className="relative mb-6">
                <div className="animate-spin rounded-full h-14 w-14 border-t-2 border-b-2 border-orange-500" />
                <div className="absolute inset-0 rounded-full h-14 w-14 border-2 border-slate-200" />
              </div>
              <p className="text-orange-600 text-base font-semibold">{progressMessage}</p>
              <p className="text-slate-400 text-sm mt-2">
                Analysing {repoCount} repo{repoCount !== 1 ? 's' : ''} — this typically takes 2–5 minutes
              </p>
            </div>
          )}

          {analysisStatus === 'error' && (
            <div className={`border p-5 rounded-sm ${isPrivateRepoError ? 'bg-amber-50 border-amber-300' : 'bg-red-50 border-red-300'}`}>
              {isPrivateRepoError ? (
                <>
                  <p className="text-amber-700 font-semibold text-base">Private Repository Access Denied</p>
                  <p className="text-amber-600 text-sm mt-2">{progressMessage}</p>
                  <p className="text-amber-500 text-xs mt-3">Add a GitHub token to the relevant repository card in the sidebar and retry.</p>
                </>
              ) : (
                <>
                  <p className="text-red-700 font-medium">Analysis failed</p>
                  <p className="text-red-600 text-sm mt-1">{progressMessage}</p>
                </>
              )}
              <button
                onClick={() => { setAnalysisStatus('idle'); setIsPrivateRepoError(false) }}
                className="mt-4 text-sm text-slate-500 hover:text-slate-800 underline block"
              >
                Dismiss
              </button>
            </div>
          )}

          {analysisStatus === 'complete' && analysisResult && (
            <ResultTabs
              results={analysisResult.results}
              historyResults={analysisResult.history_results}
              moduleResults={analysisResult.module_results}
              repoUrl={repos.filter(r => r.url.trim()).map(r => r.url.trim()).join(' + ')}
              jobId={jobId}
              onDownloadPDF={handleDownloadPDF}
            />
          )}
        </div>
      </main>
    </div>
  )
}

function AppShell() {
  const { user, loading } = useAuth()
  const isManager = user?.role === 'manager'
  const [view, setView] = useState(() => isManager ? 'team' : 'analysis')

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-orange-500" />
      </div>
    )
  }

  if (!user) return <LoginPage />

  const handleSetView = (v) => {
    if (v === 'team' && !isManager) return
    setView(v)
  }

  return (
    <div className="flex flex-col h-screen bg-slate-50 text-slate-900">
      <NavBar view={view} onSetView={handleSetView} />
      <div className="flex-1 overflow-hidden flex flex-col">
        {/* All views are always mounted — only visibility toggled — preserves state across tabs */}
        {isManager && (
          <div className={`flex-1 overflow-y-auto ${view === 'team' ? '' : 'hidden'}`}>
            <TeamDashboard />
          </div>
        )}
        <div className={`flex flex-1 overflow-hidden ${view === 'analysis' ? '' : 'hidden'}`}>
          <AnalysisView />
        </div>
        <div className={`flex-1 overflow-y-auto ${view === 'my-scores' ? '' : 'hidden'}`}>
          <MyScoreView />
        </div>
      </div>
    </div>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <AppShell />
    </AuthProvider>
  )
}
