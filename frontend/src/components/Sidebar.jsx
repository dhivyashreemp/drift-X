import { useRef, useState } from 'react'

function Label({ children }) {
  return (
    <span className="text-[10px] text-slate-500 block mb-1.5 font-semibold uppercase tracking-wider">
      {children}
    </span>
  )
}

function TextInput({ value, onChange, placeholder, type = 'text' }) {
  return (
    <input
      type={type}
      value={value}
      onChange={e => onChange(e.target.value)}
      placeholder={placeholder}
      className="w-full bg-white border border-slate-300 px-3 py-2 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:border-orange-500 focus:ring-1 focus:ring-orange-500/20 transition-colors rounded-sm"
    />
  )
}

function CommitSelect({ label, value, onChange, commits }) {
  if (!commits.length) return null
  return (
    <div>
      <Label>{label}</Label>
      <select
        value={value}
        onChange={e => onChange(e.target.value)}
        className="w-full bg-white border border-slate-300 px-3 py-2 text-sm text-slate-800 focus:outline-none focus:border-orange-500 transition-colors rounded-sm"
      >
        {commits.map(c => (
          <option key={c.hash} value={c.hash}>
            {c.hash.slice(0, 8)} · {c.message.slice(0, 35)} ({c.date.slice(0, 10)})
          </option>
        ))}
      </select>
    </div>
  )
}

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
      <Label>{label}</Label>
      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        className="w-full py-2 px-3 bg-white border border-dashed border-slate-300 text-slate-500 text-xs hover:border-orange-500 hover:text-orange-500 transition-colors flex items-center gap-2 rounded-sm"
      >
        <span className="text-orange-500 font-bold">+</span>
        <span>Add files — PDF / TXT / MD</span>
      </button>
      <input ref={inputRef} type="file" className="hidden" multiple accept={accept} onChange={handleChange} />
      {files.length > 0 && (
        <ul className="mt-1 border border-slate-200 divide-y divide-slate-100 rounded-sm">
          {files.map(f => (
            <li key={f.name} className="flex items-center justify-between text-xs bg-white px-2.5 py-1.5 text-slate-600">
              <span className="truncate mr-2">{f.name}</span>
              <button type="button" onClick={() => remove(f.name)} className="shrink-0 text-slate-400 hover:text-red-500 transition-colors">✕</button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function RepoCard({ repo, index, onUpdate, onFetch, onRemove, canRemove }) {
  const [tokenOpen, setTokenOpen] = useState(false)
  const [tokenVisible, setTokenVisible] = useState(false)
  const fetching = repo.fetchStatus === 'loading'
  const isPrivate = repo.fetchError && (
    repo.fetchError.includes('128') ||
    repo.fetchError.toLowerCase().includes('private') ||
    repo.fetchError.toLowerCase().includes('access denied')
  )

  return (
    <div className="border border-slate-200 bg-white rounded-sm shadow-sm">
      <div className="flex items-center justify-between px-3 py-2 border-b border-slate-100 bg-slate-50 rounded-t-sm">
        <span className="text-[10px] font-semibold text-orange-600 uppercase tracking-wider">
          Repository {index + 1}
        </span>
        {canRemove && (
          <button
            type="button"
            onClick={onRemove}
            className="text-slate-400 hover:text-red-500 transition-colors text-xs leading-none"
            title="Remove this repo"
          >
            ✕
          </button>
        )}
      </div>

      <div className="p-3 space-y-3">
        <div>
          <Label>Repo URL</Label>
          <TextInput
            value={repo.url}
            onChange={v => onUpdate({ url: v })}
            placeholder="https://github.com/user/repo"
          />
        </div>

        <div>
          <Label>Branch <span className="text-slate-400 normal-case tracking-normal font-normal">(optional)</span></Label>
          <TextInput
            value={repo.branch}
            onChange={v => onUpdate({ branch: v })}
            placeholder="main"
          />
        </div>

        {/* Token collapsible */}
        <div className={`border rounded-sm transition-colors ${isPrivate ? 'border-amber-300 bg-amber-50' : 'border-slate-200'}`}>
          <button
            type="button"
            onClick={() => setTokenOpen(o => !o)}
            className="w-full flex items-center justify-between px-3 py-2 text-xs"
          >
            <span className={`flex items-center gap-2 font-semibold ${isPrivate ? 'text-amber-700' : 'text-slate-600'}`}>
              <span>🔑</span>
              <span>GitHub Token</span>
              {repo.token && <span className="text-green-600 font-normal">✓</span>}
            </span>
            <span className="text-slate-400 text-[10px]">{tokenOpen ? '▲' : '▼'}</span>
          </button>

          {tokenOpen && (
            <div className="px-3 pb-3 space-y-2 border-t border-slate-200 pt-2">
              {isPrivate && (
                <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 px-2 py-1.5 rounded-sm">
                  Private repo — enter a PAT with <strong>repo</strong> read scope.
                </p>
              )}
              <div className="relative">
                <input
                  type={tokenVisible ? 'text' : 'password'}
                  value={repo.token}
                  onChange={e => onUpdate({ token: e.target.value })}
                  placeholder="ghp_xxxxxxxxxxxxxxxxxxxx"
                  className="w-full bg-white border border-slate-300 px-3 py-2 pr-10 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:border-orange-500 font-mono transition-colors rounded-sm"
                />
                <button
                  type="button"
                  onClick={() => setTokenVisible(v => !v)}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-700 text-xs"
                >
                  {tokenVisible ? 'hide' : 'show'}
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Fetch button */}
        <button
          type="button"
          onClick={onFetch}
          disabled={fetching || !repo.url.trim()}
          className="w-full py-2 px-3 bg-white border border-slate-300 text-sm text-slate-700 hover:bg-slate-50 hover:border-slate-400 disabled:opacity-40 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2 font-medium rounded-sm"
        >
          {fetching
            ? <><span className="animate-spin inline-block">⟳</span> Cloning...</>
            : <>🔍 Fetch Repo</>}
        </button>

        {repo.fetchStatus === 'error' && (
          <p className={`text-xs px-3 py-2 border rounded-sm ${
            isPrivate
              ? 'text-amber-700 bg-amber-50 border-amber-300'
              : 'text-red-700 bg-red-50 border-red-300'
          }`}>
            {isPrivate
              ? 'Private repo — add your GitHub token above and retry.'
              : repo.fetchError}
          </p>
        )}

        {repo.fetchStatus === 'success' && (
          <p className="text-xs text-green-700 flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 bg-green-500 inline-block rounded-full" />
            {repo.commits.length} commits fetched
          </p>
        )}

        {repo.commits.length > 0 && (
          <div className="space-y-2 pt-2 border-t border-slate-100">
            <Label>Evolution Range</Label>
            <CommitSelect
              label="Head (newer)"
              value={repo.headCommit}
              onChange={v => onUpdate({ headCommit: v })}
              commits={repo.commits}
            />
            <CommitSelect
              label="Base (older)"
              value={repo.baseCommit}
              onChange={v => onUpdate({ baseCommit: v })}
              commits={[...repo.commits].reverse()}
            />
          </div>
        )}
      </div>
    </div>
  )
}

export default function Sidebar({
  repos, onUpdateRepo, onFetchRepo, onAddRepo, onRemoveRepo,
  moduleName, setModuleName,
  requirementsFiles, setRequirementsFiles,
  dosDontsFiles, setDosDontsFiles,
  onStartAnalysis, canAnalyze, analysisRunning,
}) {
  return (
    <aside className="w-72 shrink-0 bg-white border-r border-slate-200 flex flex-col overflow-y-auto">
      <div className="px-4 py-3 border-b border-slate-200 bg-slate-50">
        <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-[0.15em]">
          Repository Configuration
        </p>
      </div>

      <div className="flex-1 p-4 space-y-4">
        <div className="space-y-3">
          {repos.map((repo, idx) => (
            <RepoCard
              key={repo.id}
              repo={repo}
              index={idx}
              onUpdate={patch => onUpdateRepo(repo.id, patch)}
              onFetch={() => onFetchRepo(repo.id)}
              onRemove={() => onRemoveRepo(repo.id)}
              canRemove={repos.length > 1}
            />
          ))}
        </div>

        {repos.length < 4 && (
          <button
            type="button"
            onClick={onAddRepo}
            className="w-full py-2 px-3 border border-dashed border-slate-300 text-slate-500 text-xs hover:border-orange-500 hover:text-orange-500 transition-colors flex items-center justify-center gap-2 rounded-sm"
          >
            <span className="text-orange-500 font-bold">+</span>
            Add another repository
          </button>
        )}

        <div className="pt-1 border-t border-slate-200">
          <Label>Module Focus <span className="text-slate-400 normal-case tracking-normal font-normal">(optional)</span></Label>
          <TextInput
            value={moduleName}
            onChange={setModuleName}
            placeholder="e.g. leave, payroll, auth"
          />
        </div>

        <div className="border-t border-slate-200 pt-3 space-y-3">
          <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-[0.15em]">Documents</p>
          <FileUpload
            label="Requirement Documents *"
            files={requirementsFiles}
            setFiles={setRequirementsFiles}
            accept=".pdf,.txt,.md"
          />
          <FileUpload
            label="Do's & Don'ts"
            files={dosDontsFiles}
            setFiles={setDosDontsFiles}
            accept=".pdf,.txt,.md"
          />
        </div>
      </div>

      <div className="p-4 border-t border-slate-200 bg-slate-50">
        {requirementsFiles.length === 0 && (
          <p className="text-xs text-slate-400 mb-2 text-center">Upload requirement docs to enable analysis</p>
        )}
        <button
          onClick={onStartAnalysis}
          disabled={!canAnalyze}
          className="w-full py-2.5 px-4 bg-orange-500 hover:bg-orange-600 disabled:bg-slate-200 disabled:text-slate-400 disabled:cursor-not-allowed text-white font-bold text-sm transition-colors flex items-center justify-center gap-2 uppercase tracking-wide rounded-sm"
        >
          {analysisRunning
            ? <><span className="animate-spin inline-block">⟳</span> Running...</>
            : <>▶ Start Analysis</>}
        </button>
      </div>
    </aside>
  )
}
