/* eslint-disable react-refresh/only-export-components */
import { Suspense, lazy, type ReactElement } from 'react'
import { createBrowserRouter, Navigate } from 'react-router-dom'

import { AppShell } from '../components/layout/AppShell'
import type { AppRole } from '../lib/types'
import { useAuth } from '../providers/AuthProvider'

const DashboardPage = lazy(() => import('../pages/DashboardPage').then((module) => ({ default: module.DashboardPage })))
const DepartmentManagementPage = lazy(() =>
  import('../pages/DepartmentManagementPage').then((module) => ({ default: module.DepartmentManagementPage })),
)
const FacultyManagementPage = lazy(() =>
  import('../pages/FacultyManagementPage').then((module) => ({ default: module.FacultyManagementPage })),
)
const HeroPage = lazy(() => import('../pages/HeroPage').then((module) => ({ default: module.HeroPage })))
const HomePage = lazy(() => import('../pages/HomePage').then((module) => ({ default: module.HomePage })))
const LoginPage = lazy(() => import('../pages/LoginPage').then((module) => ({ default: module.LoginPage })))
const MarkAttendancePage = lazy(() =>
  import('../pages/MarkAttendancePage').then((module) => ({ default: module.MarkAttendancePage })),
)
const RegisterStudentPage = lazy(() =>
  import('../pages/RegisterStudentPage').then((module) => ({ default: module.RegisterStudentPage })),
)
const ReportsPage = lazy(() => import('../pages/ReportsPage').then((module) => ({ default: module.ReportsPage })))
const StudentsPage = lazy(() => import('../pages/StudentsPage').then((module) => ({ default: module.StudentsPage })))

const FullPageLoader = () => (
  <div className="flex min-h-screen items-center justify-center bg-surface">
    <div className="glass-panel rounded-2xl px-6 py-4 text-sm text-slate-600 shadow-soft">Loading workspace...</div>
  </div>
)

const withSuspense = (element: ReactElement) => <Suspense fallback={<FullPageLoader />}>{element}</Suspense>

const ProtectedLayout = () => {
  const { isAuthenticated, isBootstrapping } = useAuth()

  if (isBootstrapping) {
    return <FullPageLoader />
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  return <AppShell />
}

const RootGuard = () => {
  const { isAuthenticated, isBootstrapping } = useAuth()

  if (isBootstrapping) {
    return <FullPageLoader />
  }

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />
  }

  return withSuspense(<HeroPage />)
}

const LoginGuard = () => {
  const { isAuthenticated, isBootstrapping } = useAuth()

  if (isBootstrapping) {
    return <FullPageLoader />
  }

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />
  }

  return withSuspense(<LoginPage />)
}

const RoleGuard = ({ allowedRoles, children }: { allowedRoles: AppRole[]; children: ReactElement }) => {
  const { role, isBootstrapping } = useAuth()

  if (isBootstrapping) {
    return <FullPageLoader />
  }

  if (!role || !allowedRoles.includes(role)) {
    return <Navigate to="/dashboard" replace />
  }

  return children
}

const NotFoundPage = () => (
  <div className="flex min-h-screen items-center justify-center bg-surface">
    <div className="glass-panel rounded-3xl p-8 text-center shadow-soft">
      <h1 className="font-display text-3xl text-brand-900">404</h1>
      <p className="mt-2 text-sm text-slate-600">Page not found.</p>
      <a
        href="/dashboard"
        className="mt-4 inline-flex rounded-xl bg-brand-900 px-4 py-2 text-sm font-semibold text-white"
      >
        Go to Dashboard
      </a>
    </div>
  </div>
)

export const router = createBrowserRouter([
  {
    path: '/',
    element: <RootGuard />,
  },
  {
    path: '/home',
    element: withSuspense(<HomePage />),
  },
  {
    path: '/login',
    element: <LoginGuard />,
  },
  {
    path: '/dashboard',
    element: <ProtectedLayout />,
    children: [
      { index: true, element: withSuspense(<DashboardPage />) },
      { path: 'students', element: withSuspense(<StudentsPage />) },
      {
        path: 'register-student',
        element: (
          <RoleGuard allowedRoles={['faculty', 'hod']}>
            {withSuspense(<RegisterStudentPage />)}
          </RoleGuard>
        ),
      },
      {
        path: 'mark-attendance',
        element: (
          <RoleGuard allowedRoles={['faculty']}>
            {withSuspense(<MarkAttendancePage />)}
          </RoleGuard>
        ),
      },
      {
        path: 'faculty-management',
        element: (
          <RoleGuard allowedRoles={['admin', 'hod']}>
            {withSuspense(<FacultyManagementPage />)}
          </RoleGuard>
        ),
      },
      {
        path: 'department-management',
        element: (
          <RoleGuard allowedRoles={['admin']}>
            {withSuspense(<DepartmentManagementPage />)}
          </RoleGuard>
        ),
      },
      { path: 'reports', element: withSuspense(<ReportsPage />) },
    ],
  },
  {
    path: '*',
    element: <NotFoundPage />,
  },
])
