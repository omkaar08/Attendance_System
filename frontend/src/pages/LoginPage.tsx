import { useState } from 'react'
import { motion } from 'framer-motion'
import { KeyRound, Mail, ShieldCheck, Eye, EyeOff, ArrowRight } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

import { getErrorMessage } from '../lib/api'
import { useAuth } from '../providers/AuthProvider'

export const LoginPage = () => {
  const navigate = useNavigate()
  const { login } = useAuth()

  const [email, setEmail] = useState('faculty@visionattend.com')
  const [password, setPassword] = useState('VisionAttendFaculty!123')
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [showPassword, setShowPassword] = useState(false)



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
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-brand-50/30 to-slate-50 flex flex-col">
      {/* Animated background elements */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-20 left-10 w-72 h-72 bg-brand-200/20 rounded-full blur-3xl"></div>
        <div className="absolute bottom-20 right-10 w-96 h-96 bg-brand-100/20 rounded-full blur-3xl"></div>
      </div>

      <div className="relative flex-1 flex flex-col">
        {/* Header */}
        <motion.header
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="sticky top-0 z-40 px-6 py-4 md:px-8 md:py-6 border-b border-blue-100/60 bg-gradient-to-r from-white/85 via-slate-50/70 to-blue-50/50 backdrop-blur-xl shadow-md shadow-blue-100/30"
        >
          <div className="mx-auto max-w-7xl flex items-center justify-between">
            <div className="flex items-center gap-3">
              <img src="/visionattend-logo.svg" alt="VISIONATTEND" className="h-12 w-12" />
              <div>
                <p className="font-display text-lg font-bold text-slate-900">VISIONATTEND</p>
                <p className="text-xs text-slate-500 tracking-wide">AI Attendance System</p>
              </div>
            </div>
            <a href="/" className="text-sm font-medium text-slate-600 hover:text-brand-600 transition">
              Back to Home
            </a>
          </div>
        </motion.header>

        {/* Main Content */}
        <div className="flex-1 flex items-center justify-center px-4 py-8">
          <div className="w-full max-w-7xl grid grid-cols-1 lg:grid-cols-2 gap-8 lg:gap-12 items-center">
            {/* Left Section - Features */}
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.6, delay: 0.1 }}
              className="space-y-8 p-8 rounded-2xl bg-gradient-to-br from-white/40 via-slate-50/30 to-blue-50/20 backdrop-blur border border-blue-100/40 shadow-lg"
            >
              <div>
                <h2 className="font-display text-4xl font-bold text-slate-900 leading-tight">
                  Smart Attendance with <span className="bg-gradient-to-r from-blue-600 to-cyan-600 bg-clip-text text-transparent">AI Recognition</span>
                </h2>
                <p className="mt-3 text-slate-600 text-lg">
                  Experience the future of attendance management. Fast, accurate, and secure.
                </p>
              </div>

              <div className="space-y-4">
                {[
                  { icon: '🎯', title: 'Instant Recognition', desc: '99% accuracy in seconds', bg: 'from-blue-50 to-blue-100', border: 'border-blue-200/60', accent: 'text-blue-600' },
                  { icon: '📊', title: 'Real-time Analytics', desc: 'Live attendance insights', bg: 'from-blue-50 to-blue-100', border: 'border-blue-200/60', accent: 'text-blue-600' },
                  { icon: '🔒', title: 'Enterprise Secure', desc: 'Bank-grade encryption', bg: 'from-blue-50 to-blue-100', border: 'border-blue-200/60', accent: 'text-blue-600' },
                ].map(({ icon, title, desc, bg, border, accent }) => (
                  <motion.div
                    key={title}
                    className={`flex gap-4 p-5 rounded-2xl bg-gradient-to-br ${bg} backdrop-blur-md border ${border} shadow-md hover:shadow-lg transition hover:scale-105`}
                    whileHover={{ y: -4 }}
                  >
                    <div className={`text-4xl ${accent}`}>{icon}</div>
                    <div className="flex-1">
                      <p className={`font-bold ${accent}`}>{title}</p>
                      <p className="text-sm text-slate-600 mt-1">{desc}</p>
                    </div>
                  </motion.div>
                ))}
              </div>
            </motion.div>

            {/* Right Section - Form */}
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.6 }}
            >
              <div className="glass-panel rounded-2xl border border-white/80 p-8 shadow-xl backdrop-blur-md">
                <div className="mb-8">
                  <div className="inline-flex items-center gap-2 rounded-full bg-brand-100 px-3 py-1 text-xs font-semibold text-brand-700 mb-4">
                    <ShieldCheck className="h-3.5 w-3.5" />
                    Secure Login
                  </div>
                  <h1 className="font-display text-3xl font-bold text-slate-900">Welcome Back</h1>
                  <p className="mt-2 text-sm text-slate-600">Sign in to your VISIONATTEND account</p>
                </div>

                <form className="space-y-5" onSubmit={handleSubmit}>
                  {/* Email Input */}
                  <div className="space-y-2">
                    <label htmlFor="email" className="block text-xs font-semibold uppercase tracking-wider text-slate-600">
                      Email Address
                    </label>
                    <div className="relative group">
                      <div className="absolute inset-0 bg-gradient-to-r from-brand-600 to-brand-700 rounded-xl opacity-0 group-focus-within:opacity-10 transition blur"></div>
                      <div className="relative flex items-center gap-3 rounded-xl border border-slate-200 bg-white px-4 py-3.5 transition group-focus-within:border-brand-500 group-focus-within:shadow-lg">
                        <Mail className="h-5 w-5 text-slate-400 group-focus-within:text-brand-600 transition" />
                        <input
                          id="email"
                          className="w-full bg-transparent text-sm font-medium text-slate-900 placeholder-slate-400 outline-none"
                          type="email"
                          placeholder="your@institutional.edu"
                          value={email}
                          onChange={(event) => setEmail(event.target.value)}
                          required
                        />
                      </div>
                    </div>
                  </div>

                  {/* Password Input */}
                  <div className="space-y-2">
                    <label htmlFor="password" className="block text-xs font-semibold uppercase tracking-wider text-slate-600">
                      Password
                    </label>
                    <div className="relative group">
                      <div className="absolute inset-0 bg-gradient-to-r from-brand-600 to-brand-700 rounded-xl opacity-0 group-focus-within:opacity-10 transition blur"></div>
                      <div className="relative flex items-center gap-3 rounded-xl border border-slate-200 bg-white px-4 py-3.5 transition group-focus-within:border-brand-500 group-focus-within:shadow-lg">
                        <KeyRound className="h-5 w-5 text-slate-400 group-focus-within:text-brand-600 transition" />
                        <input
                          id="password"
                          className="w-full bg-transparent text-sm font-medium text-slate-900 placeholder-slate-400 outline-none"
                          type={showPassword ? 'text' : 'password'}
                          placeholder="••••••••"
                          value={password}
                          onChange={(event) => setPassword(event.target.value)}
                          required
                        />
                        <button
                          type="button"
                          onClick={() => setShowPassword(!showPassword)}
                          className="text-slate-400 hover:text-slate-600 transition"
                        >
                          {showPassword ? (
                            <EyeOff className="h-5 w-5" />
                          ) : (
                            <Eye className="h-5 w-5" />
                          )}
                        </button>
                      </div>
                    </div>
                  </div>

                  {/* Error Message */}
                  {error && (
                    <motion.div
                      initial={{ opacity: 0, y: -4 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="rounded-xl border border-rose-200 bg-rose-50/80 backdrop-blur px-4 py-3 text-sm font-medium text-rose-700 flex items-start gap-2"
                    >
                      <span className="text-rose-400 mt-0.5">⚠</span>
                      {error}
                    </motion.div>
                  )}

                  {/* Submit Button */}
                  <button
                    type="submit"
                    disabled={isSubmitting}
                    className="w-full relative group rounded-xl font-semibold py-3.5 text-white transition-all duration-300 overflow-hidden disabled:opacity-70 disabled:cursor-not-allowed"
                  >
                    <div className="absolute inset-0 bg-gradient-to-r from-brand-600 to-brand-700 group-hover:from-brand-700 group-hover:to-brand-800 transition"></div>
                    <div className="relative flex items-center justify-center gap-2">
                      {isSubmitting ? (
                        <>
                          <div className="h-4 w-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                          Signing in...
                        </>
                      ) : (
                        <>
                          Enter Dashboard
                          <ArrowRight className="h-4 w-4 group-hover:translate-x-0.5 transition" />
                        </>
                      )}
                    </div>
                  </button>

                  {/* Demo Hint */}
                  <div className="text-center">
                    <p className="text-xs text-slate-500">
                      Demo account pre-filled for quick testing
                    </p>
                  </div>
                </form>
              </div>

              {/* Footer */}
              <div className="mt-8 text-center">
                <p className="text-xs text-slate-500">
                  © 2026 VISIONATTEND. AI-powered attendance system.
                </p>
              </div>
            </motion.div>
          </div>
        </div>
      </div>
    </div>
  )
}
