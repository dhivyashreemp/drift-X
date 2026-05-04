import { useState, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'

function MicrosoftIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 21 21" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect x="1" y="1" width="9" height="9" fill="#F25022" />
      <rect x="11" y="1" width="9" height="9" fill="#7FBA00" />
      <rect x="1" y="11" width="9" height="9" fill="#00A4EF" />
      <rect x="11" y="11" width="9" height="9" fill="#FFB900" />
    </svg>
  )
}

export default function LoginPage() {
  const { login, oauthError } = useAuth()
  const [mode, setMode] = useState('login')
  const [email, setEmail] = useState('')
  const [name, setName] = useState('')
  const [password, setPassword] = useState('')
  const [inviteCode, setInviteCode] = useState('')
  const [error, setError] = useState(oauthError || '')
  const [loading, setLoading] = useState(false)
  const [msLoading, setMsLoading] = useState(false)
  const [msAvailable, setMsAvailable] = useState(false)

  useEffect(() => {
    fetch('/api/auth/providers')
      .then(r => r.ok ? r.json() : null)
      .then(d => { if (d?.microsoft) setMsAvailable(true) })
      .catch(() => {})
  }, [])

  const safeJson = async (res) => {
    try { return await res.json() } catch (_) { return null }
  }

  const handleMicrosoftLogin = async () => {
    setMsLoading(true)
    setError('')
    try {
      const res = await fetch('/api/auth/microsoft')
      const data = await safeJson(res)
      if (!res.ok || !data) throw new Error(data?.detail || 'Backend not reachable — is the API server running?')
      window.location.href = data.url
    } catch (e) {
      setError(e.message)
      setMsLoading(false)
    }
  }

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const endpoint = mode === 'login' ? '/api/auth/login' : '/api/auth/register'
      const body = mode === 'login'
        ? { email, password }
        : { email, name, password, invite_code: inviteCode }
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      const data = await safeJson(res)
      if (!res.ok || !data) throw new Error(data?.detail || 'Backend not reachable — is the API server running?')
      login(data.token, data.user)
    } catch (e) {
      setError(e.message)
    }
    setLoading(false)
  }

  return (
    <div className="min-h-screen bg-navy-950 flex">
      {/* Left accent panel */}
      <div className="hidden lg:flex w-72 bg-navy-900 border-r border-navy-700 flex-col justify-between p-8 shrink-0">
        <div>
          <div className="flex items-center gap-3 mb-10">
            <div className="w-8 h-8 bg-orange-500 flex items-center justify-center">
              <span className="text-white text-xs font-black">DX</span>
            </div>
            <div>
              <p className="text-white font-bold text-sm">Drift-X</p>
              <p className="text-orange-500/60 text-[9px] font-semibold tracking-widest uppercase">Quality Gateway</p>
            </div>
          </div>
          <div className="space-y-6">
            {[
              { icon: '⬡', title: 'Requirement Drift Detection', desc: 'AI-powered analysis against your spec docs' },
              { icon: '⬡', title: 'Feature Loss Tracking', desc: 'Catch regressions across commit history' },
              { icon: '⬡', title: 'Team Compliance View', desc: 'Daily scores for every developer' },
              { icon: '⬡', title: 'PDF Audit Reports', desc: 'Downloadable reports for QA sign-off' },
            ].map((f, i) => (
              <div key={i} className="flex gap-3">
                <span className="text-orange-500 text-xs mt-0.5 shrink-0">▸</span>
                <div>
                  <p className="text-xs font-semibold text-white">{f.title}</p>
                  <p className="text-xs text-slate-500 mt-0.5">{f.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
        <p className="text-xs text-slate-600">© 2026 Drift-X. All rights reserved.</p>
      </div>

      {/* Right login form */}
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="w-full max-w-sm">
          {/* Mobile logo */}
          <div className="flex items-center gap-3 mb-8 lg:hidden">
            <div className="w-8 h-8 bg-orange-500 flex items-center justify-center">
              <span className="text-white text-xs font-black">DX</span>
            </div>
            <div>
              <p className="text-white font-bold text-sm">Drift-X</p>
              <p className="text-orange-500/60 text-[9px] font-semibold tracking-widest uppercase">Quality Gateway</p>
            </div>
          </div>

          <h2 className="text-xl font-bold text-white mb-1">
            {mode === 'login' ? 'Sign in to your account' : 'Create an account'}
          </h2>
          <p className="text-sm text-slate-500 mb-6">
            {mode === 'login' ? 'Enter your credentials to continue' : 'Register with your office email'}
          </p>

          <div className="bg-navy-900 border border-navy-700 p-6 space-y-5">

            {/* Microsoft SSO */}
            {msAvailable && (
              <>
                <button
                  type="button"
                  onClick={handleMicrosoftLogin}
                  disabled={msLoading}
                  className="w-full flex items-center justify-center gap-3 py-2.5 bg-white hover:bg-slate-100 disabled:opacity-60 text-slate-800 font-semibold text-sm transition-colors border border-slate-200"
                >
                  {msLoading ? <span className="animate-spin text-slate-500">⟳</span> : <MicrosoftIcon />}
                  {msLoading ? 'Redirecting…' : 'Sign in with Microsoft'}
                </button>
                <div className="flex items-center gap-3">
                  <div className="flex-1 h-px bg-navy-700" />
                  <span className="text-xs text-slate-600 font-medium">OR</span>
                  <div className="flex-1 h-px bg-navy-700" />
                </div>
              </>
            )}

            {/* Mode toggle */}
            <div className="flex border border-navy-700">
              {['login', 'register'].map(m => (
                <button
                  key={m}
                  type="button"
                  onClick={() => { setMode(m); setError('') }}
                  className={`flex-1 py-2 text-xs font-semibold transition-colors uppercase tracking-wide ${
                    mode === m
                      ? 'bg-orange-500 text-white'
                      : 'text-slate-400 hover:text-white hover:bg-navy-800'
                  }`}
                >
                  {m === 'login' ? 'Sign In' : 'Register'}
                </button>
              ))}
            </div>

            {/* Form */}
            <form onSubmit={submit} className="space-y-4">
              {mode === 'register' && (
                <Field label="Full Name" type="text" value={name} onChange={setName} placeholder="Jane Smith" required />
              )}
              <Field label="Office Email" type="email" value={email} onChange={setEmail} placeholder="you@company.com" required />
              <Field
                label="Password"
                type="password"
                value={password}
                onChange={setPassword}
                placeholder={mode === 'register' ? 'Minimum 6 characters' : '••••••••'}
                required
              />
              {mode === 'register' && (
                <div>
                  <label className="text-xs text-slate-400 block mb-1.5 font-medium uppercase tracking-wide">
                    Manager Invite Code <span className="text-slate-600 normal-case tracking-normal">— optional</span>
                  </label>
                  <input
                    type="password"
                    value={inviteCode}
                    onChange={e => setInviteCode(e.target.value)}
                    placeholder="Leave blank for developer access"
                    className="w-full bg-navy-800 border border-navy-700 px-3 py-2.5 text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:border-orange-500 transition-colors"
                  />
                </div>
              )}

              {error && (
                <div className="bg-red-950/40 border border-red-800 px-3 py-2.5">
                  <p className="text-red-400 text-sm">{error}</p>
                </div>
              )}

              <button
                type="submit"
                disabled={loading}
                className="w-full py-2.5 bg-orange-500 hover:bg-orange-600 disabled:opacity-50 text-white font-semibold text-sm transition-colors uppercase tracking-wide"
              >
                {loading ? 'Please wait…' : mode === 'login' ? 'Sign In' : 'Create Account'}
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  )
}

function Field({ label, type, value, onChange, placeholder, required }) {
  return (
    <div>
      <label className="text-xs text-slate-400 block mb-1.5 font-medium uppercase tracking-wide">{label}</label>
      <input
        type={type}
        value={value}
        onChange={e => onChange(e.target.value)}
        placeholder={placeholder}
        required={required}
        className="w-full bg-navy-800 border border-navy-700 px-3 py-2.5 text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:border-orange-500 transition-colors"
      />
    </div>
  )
}
