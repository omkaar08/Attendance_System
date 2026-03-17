import { useState } from 'react'
import { motion } from 'framer-motion'
import { KeyRound, Mail, ShieldCheck } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

import { getErrorMessage } from '../lib/api'
import { useAuth } from '../providers/AuthProvider'

export const LoginPage = () => {
  const navigate = useNavigate()
  const { login } = useAuth()

  const [email, setEmail] = useState('faculty@attendrahq.com')
  const [password, setPassword] = useState('AttendraFaculty!123')
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleSubmit = async (event: { preventDefault(): void }) => {
    event.preventDefault()
    setError(null)
    setIsSubmitting(true)

    try {
      await login({ email, password })
      navigate('/dashboard', { replace: true })
    } catch (submitError) {
      setError(getErrorMessage(submitError))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="relative min-h-screen overflow-hidden bg-surface px-4 py-10 md:px-10">
      <div className="aurora aurora-top" />
      <div className="aurora aurora-bottom" />

      <div className="mx-auto grid w-full max-w-6xl gap-6 lg:grid-cols-[1.15fr_0.85fr]">
        <motion.section
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.6 }}
          className="glass-panel relative overflow-hidden rounded-[2rem] border border-white/80 p-8 shadow-soft md:p-12"
        >
          <img
            src="/hero-campus.svg"
            alt="Abstract campus illustration"
            className="pointer-events-none absolute bottom-[-0.75rem] right-[-2rem] w-[84%] opacity-30 md:opacity-45"
          />

          <div className="relative z-10">
            <div className="mb-8 flex items-center gap-3">
              <img src="/brand-mark.svg" alt="MMAttend logo" className="h-12 w-12" />
              <div>
                <p className="font-display text-xl font-semibold text-brand-900">Attendra Studio</p>
                <p className="text-xs uppercase tracking-[0.2em] text-brand-600">Faculty + HOD Console</p>
              </div>
            </div>

            <h1 className="max-w-xl font-display text-4xl font-semibold leading-tight text-brand-900 md:text-5xl">
              Attendance operations with live recognition intelligence.
            </h1>
            <p className="mt-4 max-w-lg text-base text-slate-600">
              Manage classes, register students, capture faces, and mark attendance in one modern
              operational workspace.
            </p>

            <div className="mt-8 max-w-[42rem] grid gap-3 sm:grid-cols-3">
              {[
                ['Secure Login', 'JWT + Role Guards'],
                ['Instant Analytics', 'Attendance KPIs'],
                ['Camera Workflow', 'Live Recognition'],
              ].map(([title, subtitle]) => (
                <div key={title} className="rounded-2xl bg-white/75 p-4 shadow-inner">
                  <p className="font-semibold text-brand-900">{title}</p>
                  <p className="mt-1 text-xs text-slate-500">{subtitle}</p>
                </div>
              ))}
            </div>
          </div>
        </motion.section>

        <motion.section
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.55, delay: 0.1 }}
          className="glass-panel rounded-[2rem] border border-white/80 p-8 shadow-soft"
        >
          <div className="mb-6 inline-flex items-center gap-2 rounded-full bg-brand-100 px-3 py-1 text-xs font-semibold text-brand-700">
            <ShieldCheck className="h-4 w-4" />
            Secure Access
          </div>

          <h2 className="font-display text-3xl font-semibold text-brand-900">Sign in</h2>
          <p className="mt-2 text-sm text-slate-600">Use your institutional account to continue.</p>

          <form className="mt-7 space-y-4" onSubmit={handleSubmit}>
            <label className="block">
              <span className="mb-2 block text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Email</span>
              <div className="flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-3">
                <Mail className="h-4 w-4 text-slate-400" />
                <input
                  className="w-full rounded-xl bg-transparent py-3 text-sm text-slate-800 outline-none"
                  type="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  required
                />
              </div>
            </label>

            <label className="block">
              <span className="mb-2 block text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Password</span>
              <div className="flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-3">
                <KeyRound className="h-4 w-4 text-slate-400" />
                <input
                  className="w-full rounded-xl bg-transparent py-3 text-sm text-slate-800 outline-none"
                  type="password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  required
                />
              </div>
            </label>

            {error ? (
              <div className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</div>
            ) : null}

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full rounded-xl bg-brand-900 px-4 py-3 text-sm font-semibold text-white transition hover:bg-brand-800 disabled:cursor-not-allowed disabled:opacity-70"
            >
              {isSubmitting ? 'Signing in...' : 'Enter Dashboard'}
            </button>
          </form>

          <p className="mt-5 text-xs text-slate-500">
            Tip: a working faculty test account is prefilled for quick verification.
          </p>
        </motion.section>
      </div>
    </div>
  )
}
