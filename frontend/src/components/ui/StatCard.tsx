import { motion } from 'framer-motion'
import type { LucideIcon } from 'lucide-react'

interface StatCardProps {
  title: string
  value: string
  subtitle: string
  icon: LucideIcon
  delay?: number
}

export const StatCard = ({ title, value, subtitle, icon: Icon, delay = 0 }: StatCardProps) => (
  <motion.article
    initial={{ opacity: 0, y: 20 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ delay }}
    className="glass-panel rounded-3xl border border-white/80 p-5 shadow-soft"
  >
    <div className="flex items-start justify-between gap-3">
      <div>
        <p className="text-sm text-slate-500">{title}</p>
        <p className="mt-2 font-display text-3xl font-semibold text-brand-900">{value}</p>
      </div>
      <div className="rounded-2xl bg-brand-900 p-2 text-white">
        <Icon className="h-5 w-5" />
      </div>
    </div>
    <p className="mt-4 text-xs text-slate-500">{subtitle}</p>
  </motion.article>
)
