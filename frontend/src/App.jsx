import { useState, useEffect, useRef } from 'react'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import LoginPage from './pages/LoginPage'
import NavBar from './components/NavBar'
import Sidebar from './components/Sidebar'
import ResultTabs from './components/ResultTabs'
import TeamDashboard from './components/TeamDashboard'

const POLL_MS = 3000

function AnalysisView() {
  const { authFetch } = useAuth()

  const [repoUrl, setRepoUrl] = useState('')
  const [branch, setBranch] = useState('')
  const [moduleName, setModuleName] = useState('')
  const [gitToken, setGitToken] = useState(() => localStorage.getItem('driftx_git_token') || '')
  const [requirementsFiles, setRequirementsFiles] = useState([])
  const [dosDontsFiles, setDosDontsFiles] = useState([])

  const [commits, setCommits] = useState([])
  const [headCommit, setHeadCommit] = useState('')
  const [baseCommit, setBaseCommit] = useState('')
  const [fetchStatus, setFetchStatus] = useState('idle')
  const [fetchError, setFetchError] = useState('')

  const [jobId, setJobId] = useState(null)
  const [analysisStatus, setAnalysisStatus] = useState('idle')
  const [progressMessage, setProgressMessage] = useState('')
  const [analysisResult, setAnalysisResult] = useState(null)
  const [isPrivateRepoError, setIsPrivateRepoError] = useState(false)
  const pollRef = useRef(null)

  useEffect(() => () => clearInterval(pollRef.current), [])

  const handleFetchRepo = async () => {
    if (!repoUrl.trim()) return
    setFetchStatus('loading')
    setFetchError('')
    setCommits([])
    try {
      const fd = new FormData()
      fd.append('repo_url', repoUrl.trim())
      fd.append('branch', branch.trim())
      fd.append('git_token', gitToken.trim())
      const res = await authFetch('/api/fetch-repo', { method: 'POST', body: fd })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Failed to fetch repository')
      setCommits(data.commits)
      if (data.commits.length > 0) {
        setHeadCommit(data.commits[0].hash)
        setBaseCommit(data.commits[data.commits.length - 1].hash)
      }
      setFetchStatus('success')
    } catch (e) {
      setFetchError(e.message)
      setFetchStatus('error')
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
    if (!repoUrl.trim() || requirementsFiles.length === 0) return
    setAnalysisStatus('running')
    setProgressMessage('Submitting analysis job…')
    setAnalysisResult(null)
    setIsPrivateRepoError(false)
    try {
      const fd = new FormData()
      fd.append('repo_url', repoUrl.trim())
      fd.append('branch', branch.trim())
      fd.append('git_token', gitToken.trim())
      fd.append('module_name', moduleName.trim())
      fd.append('base_commit', baseCommit)
      fd.append('head_commit', headCommit)
      requirementsFiles.forEach(f => fd.append('requirements_files', f))
      dosDontsFiles.forEach(f => fd.append('dos_donts_files', f))
      const res = await authFetch('/api/analyze', { method: 'POST', body: fd })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Failed to start analysis')
      setJobId(data.job_id)
      setProgressMessage('Analysis queued…')
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

  const canAnalyze = repoUrl.trim() && requirementsFiles.length > 0 && analysisStatus !== 'running'

  return (
    <div className="flex flex-1 overflow-hidden">
      <Sidebar
        repoUrl={repoUrl} setRepoUrl={setRepoUrl}
        branch={branch} setBranch={setBranch}
        moduleName={moduleName} setModuleName={setModuleName}
        gitToken={gitToken} setGitToken={setGitToken}
        requirementsFiles={requirementsFiles} setRequirementsFiles={setRequirementsFiles}
        dosDontsFiles={dosDontsFiles} setDosDontsFiles={setDosDontsFiles}
        commits={commits}
        headCommit={headCommit} setHeadCommit={setHeadCommit}
        baseCommit={baseCommit} setBaseCommit={setBaseCommit}
        fetchStatus={fetchStatus} fetchError={fetchError}
        onFetchRepo={handleFetchRepo}
        onStartAnalysis={handleStartAnalysis}
        canAnalyze={canAnalyze}
        analysisRunning={analysisStatus === 'running'}
      />

      <main className="flex-1 overflow-y-auto bg-navy-950">
        <div className="p-6 max-w-5xl mx-auto">
          {analysisStatus === 'idle' && !analysisResult && (
            <div className="flex flex-col items-center justify-center h-72 text-slate-600 border border-dashed border-navy-700 bg-navy-900/30">
              <div className="w-16 h-16 bg-orange-500/10 border border-orange-500/20 flex items-center justify-center mb-4">
                <span className="text-3xl">🛡️</span>
              </div>
              <p className="text-base text-slate-400 font-medium">Configure a repository and run an analysis</p>
              <p className="text-sm text-slate-600 mt-1">Add your repo URL and requirement docs to get started</p>
            </div>
          )}

          {analysisStatus === 'running' && (
            <div className="flex flex-col items-center justify-center h-72">
              <div className="relative mb-6">
                <div className="animate-spin rounded-full h-16 w-16 border-t-2 border-b-2 border-orange-500" />
                <div className="absolute inset-0 rounded-full h-16 w-16 border-2 border-navy-700" />
              </div>
              <p className="text-orange-400 text-lg font-semibold">{progressMessage}</p>
              <p className="text-slate-600 text-sm mt-2">This typically takes 2–4 minutes</p>
            </div>
          )}

          {analysisStatus === 'error' && (
            <div className={`border p-5 ${isPrivateRepoError ? 'bg-amber-950/30 border-amber-800' : 'bg-red-950/40 border-red-800'}`}>
              {isPrivateRepoError ? (
                <>
                  <p className="text-amber-400 font-semibold text-base">🔒 Private Repository Access Denied</p>
                  <p className="text-amber-300/80 text-sm mt-2">{progressMessage}</p>
                  <div className="mt-4 bg-amber-950/40 border border-amber-900 p-3 text-sm text-amber-200/80 space-y-1">
                    <p className="font-medium text-amber-300">How to fix:</p>
                    <p>1. Open the <strong>🔑 GitHub Personal Access Token</strong> field in the sidebar.</p>
                    <p>2. Enter your PAT (needs <code className="bg-navy-800 px-1">repo</code> scope).</p>
                    <p>3. Click <strong>Fetch Repository</strong> first, then <strong>Start Analysis</strong> again.</p>
                  </div>
                  <a
                    href="https://github.com/settings/tokens/new?scopes=repo&description=DriftX"
                    target="_blank"
                    rel="noreferrer"
                    className="inline-block mt-3 text-xs text-orange-400 hover:underline"
                  >
                    Generate a new GitHub PAT ↗
                  </a>
                </>
              ) : (
                <>
                  <p className="text-red-400 font-medium">Analysis failed</p>
                  <p className="text-red-300/70 text-sm mt-1">{progressMessage}</p>
                </>
              )}
              <button
                onClick={() => { setAnalysisStatus('idle'); setIsPrivateRepoError(false) }}
                className="mt-4 text-sm text-slate-500 hover:text-white underline block"
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
              repoUrl={repoUrl}
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
      <div className="min-h-screen bg-navy-950 flex items-center justify-center">
        <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-orange-500" />
      </div>
    )
  }

  if (!user) return <LoginPage />

  const handleSetView = (v) => {
    if (isManager && v !== 'team') return
    setView(v)
  }

  return (
    <div className="flex flex-col h-screen bg-navy-950 text-slate-100">
      <NavBar view={view} onSetView={handleSetView} />
      <div className="flex-1 overflow-hidden flex flex-col">
        {view === 'analysis' && !isManager
          ? <AnalysisView />
          : <div className="flex-1 overflow-y-auto"><TeamDashboard /></div>}
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
