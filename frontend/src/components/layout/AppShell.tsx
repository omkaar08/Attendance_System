import { motion } from 'framer-motion'
import {
  BarChart3,
  Building2,
  Camera,
  FileText,
  LogOut,
  NotebookTabs,
  School,
  UserPlus,
  Users2,
} from 'lucide-react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'

import { useAuth } from '../../providers/AuthProvider'
import type { AppRole } from '../../lib/types'

const navItemsByRole: Record<AppRole, Array<{ to: string; label: string; icon: typeof BarChart3 }>> = {
  faculty: [
    { to: '/dashboard', label: 'Dashboard', icon: BarChart3 },
    { to: '/dashboard/students', label: 'Students', icon: School },
    { to: '/dashboard/register-student', label: 'Register Student', icon: UserPlus },
    { to: '/dashboard/mark-attendance', label: 'Mark Attendance', icon: Camera },
    { to: '/dashboard/reports', label: 'Reports', icon: FileText },
  ],
  hod: [
    { to: '/dashboard', label: 'Dashboard', icon: BarChart3 },
    { to: '/dashboard/students', label: 'Faculty List', icon: School },
    { to: '/dashboard/register-student', label: 'Register Student', icon: UserPlus },
    { to: '/dashboard/faculty-management', label: 'Faculty & Subject Management', icon: Users2 },
    { to: '/dashboard/reports', label: 'Reports', icon: FileText },
  ],
  admin: [
    { to: '/dashboard', label: 'Dashboard', icon: BarChart3 },
    { to: '/dashboard/students', label: 'Faculty List', icon: School },
    { to: '/dashboard/faculty-management', label: 'Faculty Management', icon: Users2 },
    { to: '/dashboard/department-management', label: 'Department Management', icon: Building2 },
    { to: '/dashboard/reports', label: 'Reports', icon: FileText },
  ],
}

export const AppShell = () => {
  const { pathname } = useLocation()
  const navigate = useNavigate()
  const { logout, user, role } = useAuth()
  const visibleNavItems = role ? navItemsByRole[role] : navItemsByRole.faculty

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <div className="min-h-screen bg-surface pb-8 text-slate-800">
      <div className="mx-auto grid w-full max-w-[1400px] grid-cols-1 gap-6 px-4 pt-4 md:px-6 lg:grid-cols-[280px_1fr]">
        <aside className="glass-panel sticky top-4 hidden h-[calc(100vh-2rem)] flex-col rounded-3xl p-6 shadow-soft lg:flex">
          <div className="mb-8 flex flex-col items-center gap-4 border-b border-slate-200 pb-8">
            <img src="/visionattend-logo.svg" alt="VISIONATTEND" className="h-24 w-24 rounded-2xl" />
          </div>

          <nav className="flex-1 space-y-2">
            {visibleNavItems.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  [
                    'group flex items-center justify-between rounded-2xl px-4 py-3 text-sm font-medium transition-all duration-300',
                    isActive
                      ? 'bg-brand-900 text-white shadow-lg shadow-brand-900/20'
                      : 'text-slate-600 hover:bg-white/70 hover:text-slate-900',
                  ].join(' ')
                }
              >
                <span className="flex items-center gap-3">
                  <Icon className="h-5 w-5" />
                  {label}
                </span>
                {pathname === to ? <NotebookTabs className="h-4 w-4" /> : null}
              </NavLink>
            ))}
          </nav>

          <div className="border-t border-slate-200 pt-4">
            <div className="rounded-2xl bg-gradient-to-br from-brand-50 to-slate-50 p-4 text-center">
              <p className="font-display font-bold text-brand-900">VISIONATTEND</p>
              <p className="text-xs uppercase tracking-[0.18em] text-slate-500 mt-1">Attendance System</p>
              <p className="mt-3 text-xs font-medium text-slate-600">
                {role === 'admin' 
                  ? 'System Admin'
                  : role === 'hod'
                  ? 'Head of Department'
                  : 'Faculty Member'
                }
              </p>
            </div>
          </div>
        </aside>

        <div className="space-y-6">
          <motion.header
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            className="glass-panel flex flex-wrap items-center justify-between gap-3 rounded-3xl px-5 py-4 shadow-soft"
          >
            <div>
              <p className="text-sm text-slate-500">Welcome back</p>
              <h1 className="font-display text-2xl font-semibold text-brand-900">
                {user?.full_name || user?.email || 'Faculty'}
              </h1>
              <p className="text-xs uppercase tracking-[0.18em] text-slate-500">{role || 'user'}</p>
            </div>

            <button
              onClick={handleLogout}
              className="inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition hover:border-brand-600 hover:text-brand-700"
            >
              <LogOut className="h-4 w-4" />
              Logout
            </button>
          </motion.header>

          <nav className="glass-panel flex gap-2 overflow-auto rounded-2xl p-2 shadow-soft lg:hidden">
            {visibleNavItems.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  [
                    'inline-flex min-w-fit items-center gap-2 rounded-xl px-3 py-2 text-xs font-semibold transition',
                    isActive ? 'bg-brand-900 text-white' : 'bg-white/70 text-slate-600',
                  ].join(' ')
                }
              >
                <Icon className="h-4 w-4" />
                {label}
              </NavLink>
            ))}
          </nav>

          <main>
            <Outlet />
          </main>
        </div>
      </div>
    </div>
  )
}
