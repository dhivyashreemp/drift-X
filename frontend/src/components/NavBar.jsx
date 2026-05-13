import { useAuth } from '../contexts/AuthContext'

export default function NavBar({ view, onSetView }) {
  const { user, logout } = useAuth()
  const isManager = user?.role === 'manager'

  return (
    <header className="shrink-0 bg-slate-900 border-b border-slate-700/60 shadow-md">
      {/* Main header row */}
      <div className="h-[60px] flex items-center justify-between px-6">
        {/* Left: logo + nav */}
        <div className="flex items-center h-full gap-0">
          {/* Logo block */}
          <div className="flex items-center gap-3.5 pr-7 border-r border-slate-700 h-full">
            <div className="w-10 h-10 bg-orange-500 flex items-center justify-center shrink-0 rounded">
              <span className="text-white text-sm font-black tracking-tight">DX</span>
            </div>
            <div className="leading-none">
              <p className="text-white font-bold text-base tracking-tight">Drift-X</p>
              <p className="text-orange-400/80 text-[10px] font-semibold tracking-[0.18em] uppercase mt-0.5">
                Quality Gateway
              </p>
            </div>
          </div>

          {/* Nav tabs */}
          <nav className="flex h-full ml-1">
            {isManager && (
              <NavBtn active={view === 'team'} onClick={() => onSetView('team')}>
                Team Dashboard
              </NavBtn>
            )}
            <NavBtn active={view === 'analysis'} onClick={() => onSetView('analysis')}>
              Analysis
            </NavBtn>
            <NavBtn active={view === 'my-scores'} onClick={() => onSetView('my-scores')}>
              My Scores
            </NavBtn>
          </nav>
        </div>

        {/* Right: user info */}
        <div className="flex items-center gap-5">
          <div className="text-right hidden sm:block">
            <div className="flex items-center justify-end gap-2">
              <p className="text-sm text-slate-100 font-semibold">{user?.name}</p>
              {isManager && (
                <span className="text-[10px] bg-orange-500 text-white px-2 py-0.5 font-bold tracking-widest uppercase rounded-sm">
                  Manager
                </span>
              )}
            </div>
            <p className="text-xs text-slate-400 mt-0.5">{user?.email}</p>
          </div>

          <div className={`w-9 h-9 flex items-center justify-center text-white text-sm font-bold uppercase rounded ${
            isManager ? 'bg-orange-600' : 'bg-orange-500'
          }`}>
            {user?.name?.[0] || '?'}
          </div>

          <div className="h-6 w-px bg-slate-700" />

          <button
            onClick={logout}
            className="text-sm text-slate-400 hover:text-orange-400 transition-colors font-medium"
          >
            Sign out
          </button>
        </div>
      </div>

      {/* Sub-bar: environment / context breadcrumb */}
      <div className="h-[28px] bg-slate-800/60 border-t border-slate-700/40 flex items-center px-6 gap-4">
        <span className="text-[10px] text-slate-500 font-medium uppercase tracking-widest">
          Code Quality Intelligence Platform
        </span>
        <div className="h-3 w-px bg-slate-700" />
        <span className="text-[10px] text-slate-500">
          Powered by Amazon Bedrock
        </span>
        <div className="ml-auto flex items-center gap-2">
          <span className="w-1.5 h-1.5 rounded-full bg-green-500 inline-block" />
          <span className="text-[10px] text-slate-500 font-medium">System Operational</span>
        </div>
      </div>
    </header>
  )
}

function NavBtn({ active, onClick, children }) {
  return (
    <button
      onClick={onClick}
      className={`px-5 h-full text-sm font-semibold transition-all border-b-2 ${
        active
          ? 'border-orange-500 text-orange-400 bg-slate-800/60'
          : 'border-transparent text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
      }`}
    >
      {children}
    </button>
  )
}
