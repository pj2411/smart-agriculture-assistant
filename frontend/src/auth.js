/*
 * Small Supabase Auth REST client for the current Vite + FastAPI stack.
 * It intentionally uses only the publishable/anon key in the browser.
 * The backend verifies the resulting bearer token with Supabase Auth.
 */

const SUPABASE_URL = (import.meta.env.VITE_SUPABASE_URL || '').replace(/\/+$/, '')
const SUPABASE_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY || ''
const SESSION_KEY = 'jalsaathi_supabase_session'
const DEMO_TOKEN = 'jalsaathi-local-demo-farmer'
const SUPABASE_CONFIGURED = Boolean((import.meta.env.VITE_SUPABASE_URL || '') && (import.meta.env.VITE_SUPABASE_ANON_KEY || ''))
export const demoAuthEnabled = import.meta.env.VITE_LOCAL_DEMO_AUTH === 'true' || !SUPABASE_CONFIGURED
export const demoEmail = import.meta.env.VITE_LOCAL_DEMO_EMAIL || 'farmer@jalsaathi.local'
export const demoPassword = import.meta.env.VITE_LOCAL_DEMO_PASSWORD || 'JalSaathiDemo2026!'

export const authConfigured = Boolean((SUPABASE_URL && SUPABASE_KEY) || demoAuthEnabled)
let listeners = []

function withRedirect(path) {
  if (typeof window === 'undefined') return path
  const separator = path.includes('?') ? '&' : '?'
  return `${path}${separator}redirect_to=${encodeURIComponent(window.location.origin)}`
}

function readStoredSession() {
  if (!authConfigured || typeof window === 'undefined') return null
  try { return JSON.parse(window.localStorage.getItem(SESSION_KEY) || 'null') } catch { return null }
}

function storeSession(session) {
  if (!authConfigured || typeof window === 'undefined') return
  if (session) window.localStorage.setItem(SESSION_KEY, JSON.stringify(session))
  else window.localStorage.removeItem(SESSION_KEY)
  listeners.forEach(listener => listener(session))
}

async function supabaseRequest(path, options = {}) {
  const response = await fetch(`${SUPABASE_URL}${path}`, {
    ...options,
    headers: { apikey: SUPABASE_KEY, 'Content-Type': 'application/json', ...(options.headers || {}) }
  })
  const body = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(body.msg || body.error_description || body.message || 'Supabase authentication request failed.')
  return body
}

async function refreshIfNeeded(session) {
  if (!session?.refresh_token) return session
  const expiry = Number(session.expires_at || 0) * 1000
  if (expiry > Date.now() + 60_000) return session
  try {
    const refreshed = await supabaseRequest('/auth/v1/token?grant_type=refresh_token', {
      method: 'POST', body: JSON.stringify({ refresh_token: session.refresh_token })
    })
    const next = { ...refreshed, expires_at: Math.floor(Date.now() / 1000) + Number(refreshed.expires_in || 3600) }
    storeSession(next)
    return next
  } catch {
    storeSession(null)
    return null
  }
}

export async function getSession() {
  if (!authConfigured) return null
  if (demoAuthEnabled) {
    const stored = readStoredSession()
    return stored?.is_demo ? stored : null
  }
  return refreshIfNeeded(readStoredSession())
}

export async function getAccessToken() {
  const session = await getSession()
  return session?.access_token || ''
}

export async function signIn(email, password) {
  if (demoAuthEnabled) {
    if (email.trim().toLowerCase() !== demoEmail.toLowerCase() || password !== demoPassword) {
      throw new Error(`Use the local demo account: ${demoEmail}`)
    }
    const session = { access_token: DEMO_TOKEN, refresh_token: DEMO_TOKEN, expires_at: Math.floor(Date.now() / 1000) + 86400, user: { id: 'local-demo-farmer', email: demoEmail }, is_demo: true }
    storeSession(session)
    return session
  }
  const session = await supabaseRequest('/auth/v1/token?grant_type=password', {
    method: 'POST', body: JSON.stringify({ email, password })
  })
  const normalized = { ...session, expires_at: Math.floor(Date.now() / 1000) + Number(session.expires_in || 3600) }
  storeSession(normalized)
  return normalized
}

export async function signUp(email, password) {
  if (demoAuthEnabled) throw new Error(`Email signup is disabled in local demo mode. Use ${demoEmail}.`)
  const body = await supabaseRequest(withRedirect('/auth/v1/signup'), {
    method: 'POST', body: JSON.stringify({ email, password })
  })
  if (body.access_token) {
    const normalized = { ...body, expires_at: Math.floor(Date.now() / 1000) + Number(body.expires_in || 3600) }
    storeSession(normalized)
    return { session: normalized, requiresEmailConfirmation: false }
  }
  return { session: null, requiresEmailConfirmation: true }
}

export async function resendSignupConfirmation(email) {
  if (demoAuthEnabled) throw new Error('Email confirmation is disabled in local demo mode.')
  return supabaseRequest(withRedirect('/auth/v1/resend'), {
    method: 'POST',
    body: JSON.stringify({ type: 'signup', email })
  })
}

function consumeRedirectSession() {
  if (!authConfigured || typeof window === 'undefined' || !window.location.hash) return null
  const params = new URLSearchParams(window.location.hash.slice(1))
  const accessToken = params.get('access_token')
  const refreshToken = params.get('refresh_token')
  if (!accessToken || !refreshToken) return null
  const session = {
    access_token: accessToken,
    refresh_token: refreshToken,
    token_type: params.get('token_type') || 'bearer',
    expires_in: Number(params.get('expires_in') || 3600),
    expires_at: Math.floor(Date.now() / 1000) + Number(params.get('expires_in') || 3600)
  }
  window.history.replaceState({}, document.title, `${window.location.pathname}${window.location.search}`)
  storeSession(session)
  return session
}

export async function signOut() {
  if (demoAuthEnabled) {
    storeSession(null)
    return
  }
  const token = await getAccessToken()
  if (token && authConfigured) {
    await supabaseRequest('/auth/v1/logout', { method: 'POST', headers: { Authorization: `Bearer ${token}` } }).catch(() => {})
  }
  storeSession(null)
}

export function subscribeAuth(listener) {
  listeners.push(listener)
  const redirectedSession = consumeRedirectSession()
  if (!redirectedSession) getSession().then(listener).catch(() => listener(null))
  return () => { listeners = listeners.filter(item => item !== listener) }
}

