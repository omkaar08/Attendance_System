import { motion } from 'framer-motion'

interface PageHeaderProps {
  eyebrow: string
  title: string
  description: string
}

export const PageHeader = ({ eyebrow, title, description }: PageHeaderProps) => (
  <motion.div
    initial={{ opacity: 0, y: 8 }}
    animate={{ opacity: 1, y: 0 }}
    className="mb-6"
  >
    <p className="text-xs uppercase tracking-[0.2em] text-brand-700">{eyebrow}</p>
    <h2 className="mt-2 font-display text-3xl font-semibold text-brand-900">{title}</h2>
    <p className="mt-2 max-w-2xl text-sm text-slate-600">{description}</p>
  </motion.div>
)
