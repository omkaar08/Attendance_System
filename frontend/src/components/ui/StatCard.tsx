import { motion } from 'framer-motion'
import type { LucideIcon } from 'lucide-react'

interface StatCardProps {
  title: string
  value: string
  subtitle: string
  icon: LucideIcon
  delay?: number
  isLoading?: boolean
}

export const StatCard = ({ title, value, subtitle, icon: Icon, delay = 0, isLoading = false }: StatCardProps) => (
  <motion.article
    initial={{ opacity: 0, y: 20 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ delay }}
    className="glass-panel rounded-3xl border border-white/80 p-6 shadow-soft hover:shadow-md transition-shadow"
  >
    <div className="flex items-start justify-between gap-4">
      <div className="flex-1">
        <p className="text-sm font-medium text-slate-500">{title}</p>
        {isLoading ? (
          <div className="mt-3 h-9 w-24 animate-pulse rounded-lg bg-slate-200" />
        ) : (
          <p className="mt-3 font-display text-4xl font-bold text-brand-900">{value}</p>
        )}
      </div>
      <div className="rounded-2xl bg-gradient-to-br from-brand-700 to-brand-900 p-3 text-white shadow-md">
        <Icon className="h-6 w-6" />
      </div>
    </div>
    <p className="mt-5 text-sm font-medium text-slate-600 leading-relaxed">{subtitle}</p>
  </motion.article>
)
