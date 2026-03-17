import { useEffect, useState } from 'react'

import { useQuery } from '@tanstack/react-query'
import { Building2, ShieldCheck } from 'lucide-react'

import { PageHeader } from '../components/ui/PageHeader'
import { getErrorMessage, managementApi } from '../lib/api'

export const DepartmentManagementPage = () => {
  const departmentsQuery = useQuery({
    queryKey: ['managed-departments'],
    queryFn: managementApi.listDepartments,
  })

  const [name, setName] = useState('')
  const [code, setCode] = useState('')

  const [selectedDepartmentId, setSelectedDepartmentId] = useState('')
  const [hodName, setHodName] = useState('')
  const [hodEmail, setHodEmail] = useState('')
  const [hodPassword, setHodPassword] = useState('')
  const [hodEmployeeCode, setHodEmployeeCode] = useState('')
  const [hodDesignation, setHodDesignation] = useState('Head of Department')

  const [isSavingDepartment, setIsSavingDepartment] = useState(false)
  const [isSavingHod, setIsSavingHod] = useState(false)


  const [status, setStatus] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const firstDepartmentId = departmentsQuery.data?.items[0]?.id
    if (!selectedDepartmentId && firstDepartmentId) {
      setSelectedDepartmentId(firstDepartmentId)
    }
  }, [departmentsQuery.data?.items, selectedDepartmentId])

  const departments = departmentsQuery.data?.items ?? []

  const renderDepartmentRows = () => {
    if (departmentsQuery.isLoading) {
      return (
        <tr>
          <td colSpan={5} className="py-5 text-slate-500">Loading departments...</td>
        </tr>
      )
    }

    if (departments.length === 0) {
      return (
        <tr>
          <td colSpan={5} className="py-5 text-slate-500">No departments configured yet.</td>
        </tr>
      )
    }

    return departments.map((department) => (
      <tr key={department.id} className="border-b border-slate-100">
        <td className="py-3">
          <p className="font-semibold text-brand-900">{department.name}</p>
          <p className="text-xs text-slate-500">{department.code}</p>
        </td>
        <td className="py-3 text-slate-700">{department.total_faculty}</td>
        <td className="py-3 text-slate-700">{department.total_subjects}</td>
        <td className="py-3 text-slate-700">{department.total_students}</td>
        <td className="py-3 text-slate-700">{department.hod_name ?? 'Not assigned'}</td>
      </tr>
    ))
  }

  const handleCreateDepartment = async (event: { preventDefault(): void }) => {
    event.preventDefault()
    setStatus(null)
    setError(null)
    setIsSavingDepartment(true)

    try {
      await managementApi.createDepartment({
        name,
        code,
      })
      await departmentsQuery.refetch()
      setStatus(`Department ${name} created.`)
      setName('')
      setCode('')
    } catch (submitError) {
      setError(getErrorMessage(submitError))
    } finally {
      setIsSavingDepartment(false)
    }
  }



  const handleAssignHod = async (event: { preventDefault(): void }) => {
    event.preventDefault()
    if (!selectedDepartmentId) {
      return
    }

    setStatus(null)
    setError(null)
    setIsSavingHod(true)

    try {
      await managementApi.createOrAssignHod(selectedDepartmentId, {
        full_name: hodName,
        email: hodEmail,
        password: hodPassword,
        employee_code: hodEmployeeCode,
        designation: hodDesignation,
      })

      await departmentsQuery.refetch()
      setStatus(`HOD assigned to selected department.`)
      setHodName('')
      setHodEmail('')
      setHodPassword('')
      setHodEmployeeCode('')
      setHodDesignation('Head of Department')
    } catch (submitError) {
      setError(getErrorMessage(submitError))
    } finally {
      setIsSavingHod(false)
    }
  }

  return (
    <section>
      <PageHeader
        eyebrow="Admin Console"
        title="Department & HOD Management"
        description="Manage department lifecycle, monitor health metrics, and assign or replace HOD ownership."
      />

      <div className="grid gap-6 xl:grid-cols-[1fr_1fr]">
        <article className="glass-panel rounded-3xl p-6 shadow-soft">
          <div className="flex items-center gap-2">
            <Building2 className="h-5 w-5 text-brand-700" />
            <h3 className="font-display text-xl font-semibold text-brand-900">Create Department</h3>
          </div>
          <p className="mt-1 text-sm text-slate-500">Set up a new academic department for onboarding faculty and students.</p>

          <form className="mt-4 space-y-3" onSubmit={handleCreateDepartment}>
            <div className="grid gap-3 md:grid-cols-2">
              <label className="block">
                <span className="mb-1 block text-xs uppercase tracking-[0.16em] text-slate-500">Department Name</span>
                <input
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                  className="w-full rounded-xl border border-slate-300 bg-white px-3 py-3 text-sm outline-none focus:border-brand-600"
                  required
                />
              </label>

              <label className="block">
                <span className="mb-1 block text-xs uppercase tracking-[0.16em] text-slate-500">Department Code</span>
                <input
                  value={code}
                  onChange={(event) => setCode(event.target.value.toUpperCase())}
                  className="w-full rounded-xl border border-slate-300 bg-white px-3 py-3 text-sm outline-none focus:border-brand-600"
                  required
                />
              </label>
            </div>

            <button
              type="submit"
              disabled={isSavingDepartment}
              className="inline-flex w-full items-center justify-center rounded-xl bg-brand-900 px-4 py-3 text-sm font-semibold text-white hover:bg-brand-800 disabled:opacity-70"
            >
              {isSavingDepartment ? 'Creating department...' : 'Create Department'}
            </button>
          </form>
        </article>

        <article className="glass-panel rounded-3xl p-6 shadow-soft">
          <div className="flex items-center gap-2">
            <ShieldCheck className="h-5 w-5 text-brand-700" />
            <h3 className="font-display text-xl font-semibold text-brand-900">Assign HOD</h3>
          </div>
          <p className="mt-1 text-sm text-slate-500">Create a new HOD account or rebind an existing account by email.</p>

          <form className="mt-4 space-y-3" onSubmit={handleAssignHod}>
            <label className="block">
              <span className="mb-1 block text-xs uppercase tracking-[0.16em] text-slate-500">Department</span>
              <select
                value={selectedDepartmentId}
                onChange={(event) => setSelectedDepartmentId(event.target.value)}
                className="w-full rounded-xl border border-slate-300 bg-white px-3 py-3 text-sm outline-none focus:border-brand-600"
                required
              >
                {departments.map((department) => (
                  <option key={department.id} value={department.id}>
                    {department.code} · {department.name}
                  </option>
                ))}
              </select>
            </label>

            <div className="grid gap-3 md:grid-cols-2">
              <label className="block">
                <span className="mb-1 block text-xs uppercase tracking-[0.16em] text-slate-500">Full Name</span>
                <input
                  value={hodName}
                  onChange={(event) => setHodName(event.target.value)}
                  className="w-full rounded-xl border border-slate-300 bg-white px-3 py-3 text-sm outline-none focus:border-brand-600"
                  required
                />
              </label>

              <label className="block">
                <span className="mb-1 block text-xs uppercase tracking-[0.16em] text-slate-500">Employee Code</span>
                <input
                  value={hodEmployeeCode}
                  onChange={(event) => setHodEmployeeCode(event.target.value)}
                  className="w-full rounded-xl border border-slate-300 bg-white px-3 py-3 text-sm outline-none focus:border-brand-600"
                  required
                />
              </label>
            </div>

            <div className="grid gap-3 md:grid-cols-2">
              <label className="block">
                <span className="mb-1 block text-xs uppercase tracking-[0.16em] text-slate-500">Email</span>
                <input
                  type="email"
                  value={hodEmail}
                  onChange={(event) => setHodEmail(event.target.value)}
                  className="w-full rounded-xl border border-slate-300 bg-white px-3 py-3 text-sm outline-none focus:border-brand-600"
                  required
                />
              </label>

              <label className="block">
                <span className="mb-1 block text-xs uppercase tracking-[0.16em] text-slate-500">Temporary Password</span>
                <input
                  type="password"
                  value={hodPassword}
                  onChange={(event) => setHodPassword(event.target.value)}
                  className="w-full rounded-xl border border-slate-300 bg-white px-3 py-3 text-sm outline-none focus:border-brand-600"
                  required
                />
              </label>
            </div>

            <label className="block">
              <span className="mb-1 block text-xs uppercase tracking-[0.16em] text-slate-500">Designation</span>
              <input
                value={hodDesignation}
                onChange={(event) => setHodDesignation(event.target.value)}
                className="w-full rounded-xl border border-slate-300 bg-white px-3 py-3 text-sm outline-none focus:border-brand-600"
                required
              />
            </label>

            <button
              type="submit"
              disabled={isSavingHod}
              className="inline-flex w-full items-center justify-center rounded-xl bg-brand-900 px-4 py-3 text-sm font-semibold text-white hover:bg-brand-800 disabled:opacity-70"
            >
              {isSavingHod ? 'Assigning HOD...' : 'Assign HOD'}
            </button>
          </form>
        </article>
      </div>

      {status ? <p className="mt-4 rounded-xl bg-emerald-50 px-3 py-2 text-sm text-emerald-700">{status}</p> : null}
      {error ? <p className="mt-4 rounded-xl bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</p> : null}

      <div className="mt-6 glass-panel rounded-3xl p-5 shadow-soft">
        <h3 className="font-display text-lg font-semibold text-brand-900">Department Directory</h3>
        <p className="mt-1 text-sm text-slate-500">Operational summary with attendance health per department.</p>

        <div className="mt-4 overflow-x-auto">
          <table className="w-full min-w-[900px] text-left text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-xs uppercase tracking-[0.16em] text-slate-500">
                <th className="py-3">Department</th>
                <th className="py-3">Faculty</th>
                <th className="py-3">Subjects</th>
                <th className="py-3">Students</th>
                <th className="py-3">HOD Assigned</th>
              </tr>
            </thead>
            <tbody>
              {renderDepartmentRows()}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  )
}
