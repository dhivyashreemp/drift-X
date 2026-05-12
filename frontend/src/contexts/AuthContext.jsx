import { createContext, useContext, useState, useEffect } from 'react'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [token, setToken] = useState(null)
  const [loading, setLoading] = useState(true)
  const [oauthError, setOauthError] = useState('')

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const urlToken = params.get('token')
    const urlError = params.get('auth_error')

    // Clean query params from URL immediately
    if (urlToken || urlError) {
      window.history.replaceState({}, '', window.location.pathname)
    }

    if (urlError) {
      setOauthError(decodeURIComponent(urlError))
      setLoading(false)
      return
    }

    const activeToken = urlToken || localStorage.getItem('driftx_token')
    if (!activeToken) {
      setLoading(false)
      return
    }

    if (urlToken) localStorage.setItem('driftx_token', urlToken)

    const apiBase = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '')
    fetch(`${apiBase}/api/auth/me`, { headers: { Authorization: `Bearer ${activeToken}` } })
      .then(r => r.ok ? r.json() : null)
      .then(u => {
        if (u) {
          setUser(u)
          setToken(activeToken)
        } else {
          _clearStorage()
        }
      })
      .catch(() => _clearStorage())
      .finally(() => setLoading(false))
  }, [])

  const _clearStorage = () => {
    localStorage.removeItem('driftx_token')
  }

  const login = (newToken, newUser) => {
    localStorage.setItem('driftx_token', newToken)
    setToken(newToken)
    setUser(newUser)
  }

  const logout = () => {
    localStorage.removeItem('driftx_token')
    setToken(null)
    setUser(null)
  }

  const authFetch = (url, options = {}) => {
    const t = token || localStorage.getItem('driftx_token')
    const base = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '')
    return fetch(`${base}${url}`, {
      ...options,
      headers: { ...options.headers, Authorization: `Bearer ${t}` },
    })
  }

  return (
    <AuthContext.Provider value={{ user, token, loading, oauthError, login, logout, authFetch }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
