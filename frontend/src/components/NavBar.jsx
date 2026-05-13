import { useAuth } from '../contexts/AuthContext'

export default function NavBar({ view, onSetView }) {
  const { user, logout } = useAuth()
  const isManager = user?.role === 'manager'

  return (
    <div className="h-13 bg-slate-800 border-b border-slate-700 flex items-center justify-between px-6 shrink-0">
      <div className="flex items-center gap-0">
        {/* Logo */}
        <div className="flex items-center gap-3 pr-6 border-r border-slate-700 h-13">
          <div className="w-7 h-7 bg-orange-500 flex items-center justify-center shrink-0 rounded-sm">
            <span className="text-white text-[11px] font-black tracking-tight">DX</span>
          </div>
          <div className="leading-none">
            <p className="text-white font-bold text-sm tracking-tight">Drift-X</p>
            <p className="text-orange-400/70 text-[9px] font-semibold tracking-[0.15em] uppercase">Quality Gateway</p>
          </div>
        </div>

        {/* Nav tabs */}
        <div className="flex h-13">
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
        </div>
      </div>

      {/* User section */}
      <div className="flex items-center gap-4">
        <div className="text-right hidden sm:block">
          <div className="flex items-center justify-end gap-2">
            <p className="text-xs text-slate-200 font-medium">{user?.name}</p>
            {isManager && (
              <span className="text-[10px] bg-orange-500 text-white px-1.5 py-0.5 font-semibold tracking-wide uppercase rounded-sm">
                Manager
              </span>
            )}
          </div>
          <p className="text-[11px] text-slate-400 mt-0.5">{user?.email}</p>
        </div>
        <div className={`w-7 h-7 flex items-center justify-center text-white text-xs font-bold uppercase rounded-sm ${
          isManager ? 'bg-orange-600' : 'bg-orange-500'
        }`}>
          {user?.name?.[0] || '?'}
        </div>
        <div className="h-5 w-px bg-slate-600" />
        <button
          onClick={logout}
          className="text-xs text-slate-400 hover:text-orange-400 transition-colors font-medium"
        >
          Sign out
        </button>
      </div>
    </div>
  )
}

function NavBtn({ active, onClick, children }) {
  return (
    <button
      onClick={onClick}
      className={`px-4 h-full text-xs font-semibold transition-all border-b-2 ${
        active
          ? 'border-orange-500 text-orange-400 bg-slate-700/50'
          : 'border-transparent text-slate-400 hover:text-slate-200 hover:bg-slate-700/30'
      }`}
    >
      {children}
    </button>
  )
}
