import React, { useState } from 'react'
import { LockKeyhole, LogIn, UserPlus } from 'lucide-react'
import { authConfigured, demoAuthEnabled, demoEmail, demoPassword, resendSignupConfirmation, signIn, signUp } from '../auth'

export default function AuthPanel({ onAuthenticated }) {
  const [mode, setMode] = useState('signin')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [confirmationPending, setConfirmationPending] = useState(false)

  const submit = async (event) => {
    event.preventDefault()
    setError('')
    setMessage('')
    setConfirmationPending(false)
    if (!authConfigured) {
      setError('Supabase is not configured. Add VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY to frontend/.env.')
      return
    }
    setBusy(true)
    try {
      if (mode === 'signin') {
        const session = await signIn(email.trim(), password)
        onAuthenticated?.(session)
      } else {
        const result = await signUp(email.trim(), password)
        if (result.session) onAuthenticated?.(result.session)
        else {
          setConfirmationPending(true)
          setMessage('Account created. Supabase requires email confirmation before sign-in. Check Spam/Junk and Promotions for the confirmation email.')
        }
      }
    } catch (requestError) {
      setError(requestError.message)
      if (mode === 'signin' && /confirm|verified|not confirmed/i.test(requestError.message)) setConfirmationPending(true)
    } finally { setBusy(false) }
  }

  const resendConfirmation = async () => {
    setBusy(true)
    setError('')
    setMessage('')
    try {
      await resendSignupConfirmation(email.trim())
      setMessage('A new confirmation email was requested. Check Spam/Junk and Promotions, then open the newest message.')
    } catch (requestError) {
      setError(requestError.message)
    } finally { setBusy(false) }
  }

  const useDemoAccount = async () => {
    setBusy(true)
    setError('')
    try {
      const session = await signIn(demoEmail, demoPassword)
      onAuthenticated?.(session)
    } catch (requestError) {
      setError(requestError.message)
    } finally { setBusy(false) }
  }

  return <div className="auth-card panel"><div className="auth-icon"><LockKeyhole size={22} /></div><span className="eyebrow">ACCOUNT REQUIRED</span><h3>Sign in to use live assistant features</h3><p>JalSaathi keeps the scenario lab public, but live AI and voice calls require an authenticated farmer session.</p>{demoAuthEnabled && <div className="demo-login"><div><strong>Local demo farmer</strong><p>Email delivery is rate-limited, so this temporary account works only on this local development app.</p><code>{demoEmail}</code></div><button className="primary-button" onClick={useDemoAccount} disabled={busy}><UserPlus size={17} /> Use demo account</button></div>}{!authConfigured && <div className="error-panel compact">Supabase is not configured yet. The scenario lab will continue to work.</div>}{authConfigured && !demoAuthEnabled && <form onSubmit={submit}><label>Email<input type="email" required value={email} onChange={event => setEmail(event.target.value)} placeholder="farmer@example.com" /></label><label>Password<input type="password" required minLength="6" value={password} onChange={event => setPassword(event.target.value)} placeholder="At least 6 characters" /></label><button className="primary-button" disabled={busy}>{mode === 'signin' ? <LogIn size={17} /> : <UserPlus size={17} />}{busy ? 'Working…' : mode === 'signin' ? 'Sign in' : 'Create account'}</button></form>}{message && <p className="auth-message">{message}</p>}{error && <div className="error-panel compact">{error}</div>}{confirmationPending && authConfigured && !demoAuthEnabled && <button className="text-button resend-button" onClick={resendConfirmation} disabled={busy}>Resend confirmation email</button>}{authConfigured && !demoAuthEnabled && <button className="text-button auth-switch" onClick={() => { setMode(mode === 'signin' ? 'signup' : 'signin'); setConfirmationPending(false); setError(''); setMessage('') }}>{mode === 'signin' ? 'Need an account? Create one' : 'Already registered? Sign in'}</button>}</div>
}
