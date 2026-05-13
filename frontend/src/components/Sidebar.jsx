import { useRef, useState } from 'react'

function SectionHeader({ children }) {
  return (
    <div className="px-5 py-2.5 border-b border-slate-200 bg-slate-50">
      <p className="text-[10px] font-bold text-slate-500 uppercase tracking-[0.18em]">{children}</p>
    </div>
  )
}

function Label({ children, required }) {
  return (
    <span className="text-xs text-slate-600 block mb-1.5 font-semibold">
      {children}
      {required && <span className="text-orange-500 ml-0.5">*</span>}
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
      className="w-full bg-white border border-slate-300 px-3 py-2.5 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:border-orange-500 focus:ring-2 focus:ring-orange-500/10 transition-colors rounded-sm"
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
        className="w-full bg-white border border-slate-300 px-3 py-2.5 text-sm text-slate-800 focus:outline-none focus:border-orange-500 focus:ring-2 focus:ring-orange-500/10 transition-colors rounded-sm"
      >
        {commits.map(c => (
          <option key={c.hash} value={c.hash}>
            {c.hash.slice(0, 8)} · {c.message.slice(0, 32)} ({c.date.slice(0, 10)})
          </option>
        ))}
      </select>
    </div>
  )
}

function FileUpload({ label, required, files, setFiles, accept }) {
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
      <Label required={required}>{label}</Label>
      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        className="w-full py-2.5 px-3 bg-white border border-dashed border-slate-300 text-slate-500 text-xs hover:border-orange-500 hover:text-orange-500 transition-colors flex items-center gap-2 rounded-sm"
      >
        <span className="text-orange-500 font-bold text-sm">+</span>
        <span>Add files — PDF / TXT / MD</span>
      </button>
      <input ref={inputRef} type="file" className="hidden" multiple accept={accept} onChange={handleChange} />
      {files.length > 0 && (
        <ul className="mt-1.5 border border-slate-200 divide-y divide-slate-100 rounded-sm overflow-hidden">
          {files.map(f => (
            <li key={f.name} className="flex items-center justify-between text-xs bg-white px-3 py-2 text-slate-600">
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
      {/* Card header */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-slate-100 bg-slate-50 rounded-t-sm">
        <div className="flex items-center gap-2">
          <div className="w-5 h-5 rounded-full bg-orange-100 border border-orange-300 flex items-center justify-center">
            <span className="text-[10px] font-bold text-orange-600">{index + 1}</span>
          </div>
          <span className="text-xs font-bold text-slate-700 uppercase tracking-wide">
            Repository {index + 1}
          </span>
        </div>
        {canRemove && (
          <button
            type="button"
            onClick={onRemove}
            className="text-slate-400 hover:text-red-500 transition-colors text-xs leading-none p-1"
            title="Remove this repo"
          >
            ✕
          </button>
        )}
      </div>

      <div className="p-4 space-y-3.5">
        <div>
          <Label required>Repo URL</Label>
          <TextInput
            value={repo.url}
            onChange={v => onUpdate({ url: v })}
            placeholder="https://github.com/user/repo"
          />
        </div>

        <div>
          <Label>Branch <span className="text-slate-400 font-normal">(optional)</span></Label>
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
            className="w-full flex items-center justify-between px-3.5 py-2.5 text-xs"
          >
            <span className={`flex items-center gap-2 font-semibold ${isPrivate ? 'text-amber-700' : 'text-slate-600'}`}>
              <span>🔑</span>
              <span>GitHub Token</span>
              {repo.token && <span className="text-green-600 font-normal">✓ Set</span>}
            </span>
            <span className="text-slate-400 text-[10px]">{tokenOpen ? '▲' : '▼'}</span>
          </button>

          {tokenOpen && (
            <div className="px-3.5 pb-3.5 space-y-2 border-t border-slate-200 pt-2.5">
              {isPrivate && (
                <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 px-3 py-2 rounded-sm">
                  Private repo — enter a PAT with <strong>repo</strong> read scope.
                </p>
              )}
              <div className="relative">
                <input
                  type={tokenVisible ? 'text' : 'password'}
                  value={repo.token}
                  onChange={e => onUpdate({ token: e.target.value })}
                  placeholder="ghp_xxxxxxxxxxxxxxxxxxxx"
                  className="w-full bg-white border border-slate-300 px-3 py-2.5 pr-10 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:border-orange-500 font-mono transition-colors rounded-sm"
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
          className="w-full py-2.5 px-3 bg-white border border-slate-300 text-sm text-slate-700 hover:bg-slate-50 hover:border-orange-400 hover:text-orange-600 disabled:opacity-40 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2 font-semibold rounded-sm"
        >
          {fetching
            ? <><span className="animate-spin inline-block">⟳</span> Cloning repository...</>
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
          <p className="text-xs text-green-700 flex items-center gap-2 font-medium">
            <span className="w-2 h-2 bg-green-500 inline-block rounded-full" />
            {repo.commits.length} commits fetched
          </p>
        )}

        {repo.commits.length > 0 && (
          <div className="space-y-3 pt-3 border-t border-slate-100">
            <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Evolution Range</p>
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
    <aside className="w-80 shrink-0 bg-white border-r border-slate-200 flex flex-col overflow-y-auto shadow-sm">
      <SectionHeader>Repository Configuration</SectionHeader>

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
            className="w-full py-2.5 px-3 border border-dashed border-slate-300 text-slate-500 text-xs hover:border-orange-500 hover:text-orange-500 transition-colors flex items-center justify-center gap-2 rounded-sm font-medium"
          >
            <span className="text-orange-500 font-bold text-sm">+</span>
            Add another repository
          </button>
        )}

        <div className="pt-2 border-t border-slate-200">
          <Label>Module Focus <span className="text-slate-400 font-normal">(optional)</span></Label>
          <TextInput
            value={moduleName}
            onChange={setModuleName}
            placeholder="e.g. leave, payroll, auth"
          />
          <p className="text-[10px] text-slate-400 mt-1">Narrow the analysis to a specific module or domain.</p>
        </div>

        <div className="border-t border-slate-200 pt-4 space-y-4">
          <p className="text-[10px] font-bold text-slate-500 uppercase tracking-[0.18em]">Documents</p>
          <FileUpload
            label="Requirement Documents"
            required
            files={requirementsFiles}
            setFiles={setRequirementsFiles}
            accept=".pdf,.txt,.md"
          />
          <FileUpload
            label="Do's &amp; Don'ts"
            files={dosDontsFiles}
            setFiles={setDosDontsFiles}
            accept=".pdf,.txt,.md"
          />
        </div>
      </div>

      {/* Footer / CTA */}
      <div className="p-4 border-t border-slate-200 bg-slate-50 space-y-2.5">
        {requirementsFiles.length === 0 && (
          <p className="text-xs text-slate-400 text-center">
            Upload requirement documents to enable analysis
          </p>
        )}
        <button
          onClick={onStartAnalysis}
          disabled={!canAnalyze}
          className="w-full py-3 px-4 bg-orange-500 hover:bg-orange-600 active:bg-orange-700 disabled:bg-slate-200 disabled:text-slate-400 disabled:cursor-not-allowed text-white font-bold text-sm transition-colors flex items-center justify-center gap-2.5 uppercase tracking-widest rounded-sm shadow-sm"
        >
          {analysisRunning
            ? <><span className="animate-spin inline-block">⟳</span> Running Analysis...</>
            : <>&#9654; Start Analysis</>}
        </button>
        {!analysisRunning && canAnalyze && (
          <p className="text-[10px] text-slate-400 text-center">Analysis typically takes 2–5 minutes</p>
        )}
      </div>
    </aside>
  )
}
