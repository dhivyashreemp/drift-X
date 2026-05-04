import { useRef, useState, useEffect } from 'react'

const STORAGE_KEY = 'driftx_git_token'

function FileUpload({ label, files, setFiles, accept }) {
  const inputRef = useRef(null)

  const handleChange = (e) => {
    const incoming = Array.from(e.target.files)
    setFiles(prev => {
      const existing = new Set(prev.map(f => f.name))
      return [...prev, ...incoming.filter(f => !existing.has(f.name))]
    })
    e.target.value = ''
  }

  const remove = (name) => setFiles(prev => prev.filter(f => f.name !== name))

  return (
    <div>
      <span className="text-[10px] text-slate-500 block mb-1.5 font-semibold uppercase tracking-wider">{label}</span>
      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        className="w-full py-2 px-3 bg-navy-800 border border-dashed border-navy-600 text-slate-400 text-xs hover:border-orange-500 hover:text-orange-400 transition-colors flex items-center gap-2"
      >
        <span className="text-orange-500 font-bold">+</span>
        <span>Add files — PDF / TXT / MD</span>
      </button>
      <input ref={inputRef} type="file" className="hidden" multiple accept={accept} onChange={handleChange} />
      {files.length > 0 && (
        <ul className="mt-1 border border-navy-700 divide-y divide-navy-700">
          {files.map(f => (
            <li key={f.name} className="flex items-center justify-between text-xs bg-navy-800 px-2.5 py-1.5 text-slate-300">
              <span className="truncate mr-2">{f.name}</span>
              <button type="button" onClick={() => remove(f.name)} className="shrink-0 text-slate-600 hover:text-red-400 transition-colors">✕</button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function Input({ label, value, onChange, placeholder, help }) {
  return (
    <div>
      <label className="text-[10px] text-slate-500 block mb-1.5 font-semibold uppercase tracking-wider">
        {label}
        {help && <span className="ml-1 text-slate-600 normal-case tracking-normal">({help})</span>}
      </label>
      <input
        type="text"
        value={value}
        onChange={e => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full bg-navy-800 border border-navy-700 px-3 py-2 text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:border-orange-500 transition-colors"
      />
    </div>
  )
}

function CommitSelect({ label, value, onChange, commits }) {
  if (!commits.length) return null
  return (
    <div>
      <label className="text-[10px] text-slate-500 block mb-1.5 font-semibold uppercase tracking-wider">{label}</label>
      <select
        value={value}
        onChange={e => onChange(e.target.value)}
        className="w-full bg-navy-800 border border-navy-700 px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-orange-500 transition-colors"
      >
        {commits.map(c => (
          <option key={c.hash} value={c.hash}>
            {c.hash.slice(0, 8)} · {c.message.slice(0, 40)} ({c.date.slice(0, 10)})
          </option>
        ))}
      </select>
    </div>
  )
}

function GitTokenField({ token, setToken, forceOpen }) {
  const [open, setOpen] = useState(false)
  const [visible, setVisible] = useState(false)

  useEffect(() => { if (forceOpen) setOpen(true) }, [forceOpen])

  const save = (val) => {
    setToken(val)
    localStorage.setItem(STORAGE_KEY, val)
  }

  const clear = () => {
    setToken('')
    localStorage.removeItem(STORAGE_KEY)
  }

  return (
    <div className={`border transition-colors ${forceOpen ? 'border-amber-700 bg-amber-950/20' : 'border-navy-700'}`}>
      <button
        type="button"
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between px-3 py-2 text-xs"
      >
        <span className={`flex items-center gap-2 font-semibold ${forceOpen ? 'text-amber-400' : 'text-slate-400'}`}>
          <span>🔑</span>
          <span>GitHub Personal Access Token</span>
          {token && <span className="text-green-500 font-normal">✓ saved</span>}
        </span>
        <span className="text-slate-600 text-[10px]">{open ? '▲' : '▼'}</span>
      </button>

      {open && (
        <div className="px-3 pb-3 space-y-2 border-t border-navy-700 pt-2">
          {forceOpen && (
            <p className="text-xs text-amber-400 bg-amber-950/30 border border-amber-900 px-2 py-1.5">
              Private repo detected — enter a PAT with <strong>repo</strong> scope to continue.
            </p>
          )}
          <div className="relative">
            <input
              type={visible ? 'text' : 'password'}
              value={token}
              onChange={e => save(e.target.value)}
              placeholder="ghp_xxxxxxxxxxxxxxxxxxxx"
              className="w-full bg-navy-800 border border-navy-700 px-3 py-2 pr-10 text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:border-orange-500 font-mono transition-colors"
            />
            <button
              type="button"
              onClick={() => setVisible(v => !v)}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 text-xs"
            >
              {visible ? 'hide' : 'show'}
            </button>
          </div>
          {token && (
            <button type="button" onClick={clear} className="text-xs text-slate-600 hover:text-red-400 transition-colors">
              ✕ Clear token
            </button>
          )}
          <p className="text-xs text-slate-600">
            One token works for all your private repos.{' '}
            <a
              href="https://github.com/settings/tokens/new?scopes=repo&description=DriftX"
              target="_blank"
              rel="noreferrer"
              className="text-orange-500 hover:underline"
            >
              Generate one ↗
            </a>
          </p>
        </div>
      )}
    </div>
  )
}

const isPrivateRepoError = (msg = '') =>
  msg.includes('128') || msg.toLowerCase().includes('private') ||
  msg.toLowerCase().includes('access denied') || msg.toLowerCase().includes('not found')

export default function Sidebar({
  repoUrl, setRepoUrl,
  branch, setBranch,
  moduleName, setModuleName,
  requirementsFiles, setRequirementsFiles,
  dosDontsFiles, setDosDontsFiles,
  commits,
  headCommit, setHeadCommit,
  baseCommit, setBaseCommit,
  fetchStatus, fetchError,
  onFetchRepo, onStartAnalysis,
  canAnalyze, analysisRunning,
  gitToken, setGitToken,
}) {
  const fetching = fetchStatus === 'loading'
  const showTokenPrompt = fetchStatus === 'error' && isPrivateRepoError(fetchError)

  return (
    <aside className="w-68 shrink-0 bg-navy-900 border-r border-navy-700 flex flex-col overflow-y-auto" style={{ width: '272px' }}>
      {/* Section header */}
      <div className="px-4 py-3 border-b border-navy-700 bg-navy-950/40">
        <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-[0.15em]">Repository Configuration</p>
      </div>

      <div className="flex-1 p-4 space-y-4">
        <Input label="Repository URL" value={repoUrl} onChange={setRepoUrl} placeholder="https://github.com/user/repo" />
        <Input label="Branch" value={branch} onChange={setBranch} placeholder="main" help="optional" />
        <Input label="Module Focus" value={moduleName} onChange={setModuleName} placeholder="e.g. leave, payroll" help="optional" />

        <GitTokenField token={gitToken} setToken={setGitToken} forceOpen={showTokenPrompt} />

        <div className="pt-1 border-t border-navy-700">
          <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-[0.15em] mb-3">Documents</p>
          <div className="space-y-3">
            <FileUpload label="Requirement Documents *" files={requirementsFiles} setFiles={setRequirementsFiles} accept=".pdf,.txt,.md" />
            <FileUpload label="Do's & Don'ts" files={dosDontsFiles} setFiles={setDosDontsFiles} accept=".pdf,.txt,.md" />
          </div>
        </div>

        <button
          onClick={onFetchRepo}
          disabled={fetching || !repoUrl.trim()}
          className="w-full py-2 px-4 bg-navy-800 border border-navy-600 text-sm text-slate-200 hover:bg-navy-700 hover:border-slate-500 disabled:opacity-40 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2 font-medium"
        >
          {fetching
            ? <><span className="animate-spin inline-block">⟳</span> Cloning…</>
            : <>🔍 Fetch Repository</>}
        </button>

        {fetchStatus === 'error' && (
          <div className={`text-xs px-3 py-2 border ${
            showTokenPrompt
              ? 'text-amber-400 bg-amber-950/20 border-amber-800'
              : 'text-red-400 bg-red-950/20 border-red-800'
          }`}>
            {showTokenPrompt
              ? '🔒 Private repository — enter your GitHub PAT above and try again.'
              : fetchError}
          </div>
        )}

        {fetchStatus === 'success' && (
          <p className="text-xs text-green-400 flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 bg-green-500 inline-block" />
            {commits.length} commits fetched
          </p>
        )}

        {commits.length > 0 && (
          <div className="space-y-3 pt-3 border-t border-navy-700">
            <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-[0.15em]">Evolution Range</p>
            <CommitSelect label="Head (newer)" value={headCommit} onChange={setHeadCommit} commits={commits} />
            <CommitSelect label="Base (older)" value={baseCommit} onChange={setBaseCommit} commits={[...commits].reverse()} />
          </div>
        )}
      </div>

      {/* Run button */}
      <div className="p-4 border-t border-navy-700 bg-navy-950/30">
        {requirementsFiles.length === 0 && (
          <p className="text-xs text-slate-600 mb-2 text-center">Upload requirement docs to enable analysis</p>
        )}
        <button
          onClick={onStartAnalysis}
          disabled={!canAnalyze}
          className="w-full py-2.5 px-4 bg-orange-500 hover:bg-orange-600 disabled:bg-navy-800 disabled:text-slate-600 disabled:cursor-not-allowed text-white font-bold text-sm transition-colors flex items-center justify-center gap-2 uppercase tracking-wide"
        >
          {analysisRunning
            ? <><span className="animate-spin inline-block">⟳</span> Running…</>
            : <>▶ Start Analysis</>}
        </button>
      </div>
    </aside>
  )
}
