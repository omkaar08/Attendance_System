import type {
  AttendanceReportItem,
  DailyReportRow,
  DepartmentReportRow,
  MonthlyReportRow,
  StudentReportRow,
  SubjectReportRow,
} from './types'

// -------------------------------------------------------------------------- //
//  Raw attendance report (existing)                                           //
// -------------------------------------------------------------------------- //

const toRows = (items: AttendanceReportItem[]) =>
  items.map((item) => ({
    Date: item.class_date,
    Session: item.session_label,
    Subject: item.subject_name,
    Roll: item.roll_number,
    Student: item.student_name,
    Status: item.status,
    Confidence: Math.round(item.confidence_score * 100),
  }))

export const downloadCsv = (items: AttendanceReportItem[], fileName: string): void => {
  const rows = toRows(items)
  const header = Object.keys(rows[0] ?? {})
  const body = rows.map((row) => header.map((key) => JSON.stringify(row[key as keyof typeof row] ?? '')).join(','))
  const csv = [header.join(','), ...body].join('\n')

  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = fileName
  a.click()
  URL.revokeObjectURL(url)
}

export const downloadExcel = async (items: AttendanceReportItem[], fileName: string): Promise<void> => {
  const XLSX = await import('xlsx')
  const rows = toRows(items)
  const sheet = XLSX.utils.json_to_sheet(rows)
  const book = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(book, sheet, 'Attendance')
  XLSX.writeFile(book, fileName)
}

export const downloadPdf = async (items: AttendanceReportItem[], fileName: string): Promise<void> => {
  const [{ default: jsPDF }, { default: autoTable }] = await Promise.all([
    import('jspdf'),
    import('jspdf-autotable'),
  ])
  const rows = toRows(items)
  const doc = new jsPDF({ orientation: 'landscape' })
  doc.setFontSize(16)
  doc.text('Attendance Report', 14, 14)

  autoTable(doc, {
    startY: 22,
    head: [Object.keys(rows[0] ?? { Date: '', Session: '', Subject: '', Roll: '', Student: '', Status: '', Confidence: '' })],
    body: rows.map((row) => Object.values(row)),
    styles: { fontSize: 9 },
    headStyles: { fillColor: [19, 46, 78] },
  })

  doc.save(fileName)
}

// -------------------------------------------------------------------------- //
//  Generic helper                                                             //
// -------------------------------------------------------------------------- //

const genericCsv = (data: Record<string, unknown>[], fileName: string): void => {
  if (!data.length) return
  const headers = Object.keys(data[0])
  const body = data.map((row) => headers.map((h) => JSON.stringify(row[h] ?? '')).join(','))
  const csv = [headers.join(','), ...body].join('\n')
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = fileName
  a.click()
  URL.revokeObjectURL(url)
}

const genericExcel = async (data: Record<string, unknown>[], sheetName: string, fileName: string): Promise<void> => {
  if (!data.length) return
  const XLSX = await import('xlsx')
  const sheet = XLSX.utils.json_to_sheet(data)
  const book = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(book, sheet, sheetName)
  XLSX.writeFile(book, fileName)
}

const genericPdf = async (
  title: string,
  data: Record<string, unknown>[],
  fileName: string,
  landscape = false,
): Promise<void> => {
  if (!data.length) return
  const [{ default: jsPDF }, { default: autoTable }] = await Promise.all([
    import('jspdf'),
    import('jspdf-autotable'),
  ])
  const doc = new jsPDF({ orientation: landscape ? 'landscape' : 'portrait' })
  doc.setFontSize(15)
  doc.text(title, 14, 14)
  const headers = Object.keys(data[0])
  autoTable(doc, {
    startY: 22,
    head: [headers],
    body: data.map((row) => headers.map((h) => String(row[h] ?? ''))),
    styles: { fontSize: 8 },
    headStyles: { fillColor: [19, 46, 78] },
  })
  doc.save(fileName)
}

// -------------------------------------------------------------------------- //
//  Daily report                                                               //
// -------------------------------------------------------------------------- //

const toDailyRows = (items: DailyReportRow[]) =>
  items.map((r) => ({
    Date: r.date,
    'Total Records': r.total_records,
    'Unique Students': r.unique_students,
    'Present Count': r.present_count,
    'Present %': r.present_percent,
  }))

export const downloadDailyCsv = (items: DailyReportRow[], fileName: string): void =>
  genericCsv(toDailyRows(items) as Record<string, unknown>[], fileName)

export const downloadDailyExcel = async (items: DailyReportRow[], fileName: string): Promise<void> =>
  genericExcel(toDailyRows(items) as Record<string, unknown>[], 'Daily', fileName)

export const downloadDailyPdf = async (items: DailyReportRow[], fileName: string): Promise<void> =>
  genericPdf('Daily Attendance Report', toDailyRows(items) as Record<string, unknown>[], fileName)

// -------------------------------------------------------------------------- //
//  Monthly report                                                             //
// -------------------------------------------------------------------------- //

const toMonthlyRows = (items: MonthlyReportRow[]) =>
  items.map((r) => ({
    Month: r.month_label,
    'Total Records': r.total_records,
    'Unique Students': r.unique_students,
    'Present Count': r.present_count,
    'Present %': r.present_percent,
  }))

export const downloadMonthlyCsv = (items: MonthlyReportRow[], fileName: string): void =>
  genericCsv(toMonthlyRows(items) as Record<string, unknown>[], fileName)

export const downloadMonthlyExcel = async (items: MonthlyReportRow[], fileName: string): Promise<void> =>
  genericExcel(toMonthlyRows(items) as Record<string, unknown>[], 'Monthly', fileName)

export const downloadMonthlyPdf = async (items: MonthlyReportRow[], fileName: string): Promise<void> =>
  genericPdf('Monthly Attendance Report', toMonthlyRows(items) as Record<string, unknown>[], fileName)

// -------------------------------------------------------------------------- //
//  Subject report                                                             //
// -------------------------------------------------------------------------- //

const toSubjectRows = (items: SubjectReportRow[]) =>
  items.map((r) => ({
    Subject: r.subject_name,
    Code: r.subject_code,
    Department: r.department_name,
    Faculty: r.faculty_name,
    Semester: r.semester,
    Section: r.section,
    'Total Records': r.total_records,
    'Unique Students': r.unique_students,
    Present: r.present_count,
    Absent: r.absent_count,
    Late: r.late_count,
    '%': r.attendance_percent,
  }))

export const downloadSubjectCsv = (items: SubjectReportRow[], fileName: string): void =>
  genericCsv(toSubjectRows(items) as Record<string, unknown>[], fileName)

export const downloadSubjectExcel = async (items: SubjectReportRow[], fileName: string): Promise<void> =>
  genericExcel(toSubjectRows(items) as Record<string, unknown>[], 'Subjects', fileName)

export const downloadSubjectPdf = async (items: SubjectReportRow[], fileName: string): Promise<void> =>
  genericPdf('Subject Attendance Report', toSubjectRows(items) as Record<string, unknown>[], fileName, true)

// -------------------------------------------------------------------------- //
//  Student performance report                                                 //
// -------------------------------------------------------------------------- //

const toStudentRows = (items: StudentReportRow[]) =>
  items.map((r) => ({
    Roll: r.roll_number,
    Student: r.full_name,
    Subject: r.subject_name,
    Code: r.subject_code,
    Sem: r.semester,
    Sec: r.section,
    Total: r.total_sessions,
    Present: r.present_count,
    Absent: r.absent_count,
    Late: r.late_count,
    '%': r.attendance_percent,
  }))

export const downloadStudentCsv = (items: StudentReportRow[], fileName: string): void =>
  genericCsv(toStudentRows(items) as Record<string, unknown>[], fileName)

export const downloadStudentExcel = async (items: StudentReportRow[], fileName: string): Promise<void> =>
  genericExcel(toStudentRows(items) as Record<string, unknown>[], 'Students', fileName)

export const downloadStudentPdf = async (items: StudentReportRow[], fileName: string): Promise<void> =>
  genericPdf(
    'Student Performance Report',
    toStudentRows(items) as Record<string, unknown>[],
    fileName,
    true,
  )

// -------------------------------------------------------------------------- //
//  Department report                                                          //
// -------------------------------------------------------------------------- //

const toDepartmentRows = (items: DepartmentReportRow[]) =>
  items.map((r) => ({
    Department: r.department_name,
    Code: r.department_code,
    Students: r.total_students,
    Faculty: r.total_faculty,
    Subjects: r.total_subjects,
    Sessions: r.total_sessions,
    Present: r.present_count,
    '%': r.attendance_percent,
  }))

export const downloadDepartmentCsv = (items: DepartmentReportRow[], fileName: string): void =>
  genericCsv(toDepartmentRows(items) as Record<string, unknown>[], fileName)

export const downloadDepartmentExcel = async (items: DepartmentReportRow[], fileName: string): Promise<void> =>
  genericExcel(toDepartmentRows(items) as Record<string, unknown>[], 'Departments', fileName)

export const downloadDepartmentPdf = async (items: DepartmentReportRow[], fileName: string): Promise<void> =>
  genericPdf('Department Report', toDepartmentRows(items) as Record<string, unknown>[], fileName)

