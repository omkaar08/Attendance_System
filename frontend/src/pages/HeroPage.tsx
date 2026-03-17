import { motion } from 'framer-motion'
import { ArrowRight, BarChart3, Lock, Zap } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

export const HeroPage = () => {
  const navigate = useNavigate()

  const features = [
    {
      icon: Zap,
      title: 'Instant Recognition',
      description: '99% accuracy in seconds',
    },
    {
      icon: BarChart3,
      title: 'Real-time Analytics',
      description: 'Live attendance insights',
    },
    {
      icon: Lock,
      title: 'Enterprise Secure',
      description: 'Bank-grade encryption',
    },
  ]

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1,
        delayChildren: 0.2,
      },
    },
  }

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: {
      opacity: 1,
      y: 0,
      transition: { duration: 0.5 },
    },
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-white via-slate-50 to-brand-50 relative">
      {/* Animated gradient overlay */}
      <div className="fixed inset-0 bg-gradient-to-tr from-brand-50/20 via-transparent to-blue-50/20 pointer-events-none"></div>
      
      {/* Animated background orbs */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -left-40 w-96 h-96 bg-blue-200/15 rounded-full blur-3xl animate-pulse"></div>
        <div className="absolute -bottom-40 -right-40 w-80 h-80 bg-brand-200/10 rounded-full blur-3xl animate-pulse" style={{ animationDelay: '2s' }}></div>
        <div className="absolute top-1/2 left-1/3 w-72 h-72 bg-slate-200/10 rounded-full blur-3xl animate-pulse" style={{ animationDelay: '1s' }}></div>
      </div>

      <div className="relative">
        {/* Header Navigation */}
        <motion.header
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="sticky top-0 z-50 border-b border-blue-200/70 bg-gradient-to-r from-white/85 via-slate-50/70 to-blue-50/50 backdrop-blur-xl"
        >
          <nav className="mx-auto max-w-7xl px-6 py-4 md:px-8 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <img src="/visionattend-logo.svg" alt="VISIONATTEND" className="h-14 w-14" />
              <div>
                <p className="font-display text-lg font-bold text-brand-900">VISIONATTEND</p>
                <p className="text-xs text-slate-500 tracking-wide">AI Attendance System</p>
              </div>
            </div>
            <motion.button
              onClick={() => navigate('/login')}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              className="px-6 py-2 rounded-lg font-semibold text-white bg-gradient-to-r from-brand-600 to-brand-700 hover:from-brand-700 hover:to-brand-800 transition"
            >
              Login
            </motion.button>
          </nav>
        </motion.header>

        {/* Hero Section */}
        <section className="min-h-[calc(100vh-80px)] flex items-center justify-center px-4 py-16">
          <motion.div
            variants={containerVariants}
            initial="hidden"
            animate="visible"
            className="w-full max-w-4xl text-center"
          >
            {/* Logo and Branding */}
            <motion.div variants={itemVariants} className="mb-8">
              <div className="flex justify-center mb-6">
                <motion.img
                  src="/visionattend-logo.svg"
                  alt="VISIONATTEND"
                  className="h-48 w-48"
                  whileHover={{ scale: 1.1 }}
                  transition={{ duration: 0.3 }}
                />
              </div>
              <h1 className="font-display text-5xl md:text-6xl font-bold text-slate-900 leading-tight">
                <span>Smart Attendance</span>
                <br />
                <span className="bg-gradient-to-r from-brand-600 to-brand-700 bg-clip-text text-transparent">
                  with AI Recognition
                </span>
              </h1>
            </motion.div>

            {/* Slogan */}
            <motion.div variants={itemVariants} className="mb-8">
              <div className="inline-flex items-center gap-6 px-6 py-3 rounded-full border border-blue-200/60 bg-white/40 backdrop-blur-sm">
                <span className="text-lg font-semibold text-brand-700">SEE</span>
                <div className="w-1 h-6 bg-gradient-to-b from-brand-400 to-blue-400"></div>
                <span className="text-lg font-semibold text-brand-700">RECOGNIZE</span>
                <div className="w-1 h-6 bg-gradient-to-b from-brand-400 to-blue-400"></div>
                <span className="text-lg font-semibold text-brand-700">RECORD</span>
              </div>
            </motion.div>

            {/* Tagline */}
            <motion.p
              variants={itemVariants}
              className="text-xl text-slate-600 mb-4 max-w-2xl mx-auto"
            >
              Experience the future of attendance management. Fast, accurate, and secure face recognition powered by advanced AI.
            </motion.p>

            {/* Secondary tagline */}
            <motion.p variants={itemVariants} className="text-sm text-slate-500 mb-12">
              Trusted by institutions for reliable, intelligent attendance tracking
            </motion.p>

            {/* CTA Buttons */}
            <motion.div variants={itemVariants} className="flex flex-col sm:flex-row gap-4 justify-center mb-16">
              <motion.button
                onClick={() => navigate('/login')}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                className="group relative px-8 py-4 rounded-xl font-semibold text-white bg-gradient-to-r from-brand-600 to-brand-700 hover:from-brand-700 hover:to-brand-800 transition flex items-center justify-center gap-2"
              >
                Enter Platform
                <ArrowRight className="h-5 w-5 group-hover:translate-x-1 transition" />
              </motion.button>
              <motion.a
                href="#features"
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                className="px-8 py-4 rounded-xl font-semibold text-brand-900 border-2 border-brand-600 hover:bg-brand-50 transition"
              >
                Learn More
              </motion.a>
            </motion.div>

            {/* Features Grid */}
            <motion.div
              variants={containerVariants}
              className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12"
              id="features"
            >
              {features.map((feature) => {
                const Icon = feature.icon
                return (
                  <motion.div
                    key={feature.title}
                    variants={itemVariants}
                    whileHover={{ y: -4 }}
                    className="flex flex-col gap-4 p-6 rounded-2xl bg-gradient-to-br from-blue-50 to-cyan-50 backdrop-blur-md border border-blue-200/60 shadow-md hover:shadow-lg transition hover:scale-105"
                  >
                    <div className="text-blue-600">
                      <Icon className="h-10 w-10" />
                    </div>
                    <div>
                      <h3 className="font-bold text-lg text-blue-600 mb-1">{feature.title}</h3>
                      <p className="text-sm text-slate-600">{feature.description}</p>
                    </div>
                  </motion.div>
                )
              })}
            </motion.div>

            {/* Stats */}
            <motion.div variants={containerVariants} className="grid grid-cols-3 gap-6 py-12">
              {[
                { value: '99%', label: 'Accuracy Rate' },
                { value: '3', label: 'User Roles' },
                { value: '24/7', label: 'Support' },
              ].map((stat) => (
                <motion.div
                  key={stat.label}
                  variants={itemVariants}
                  className="backdrop-blur-md bg-gradient-to-br from-white/60 via-slate-50/40 to-blue-50/30 rounded-xl p-6 border border-blue-100/50 hover:border-blue-200/70 transition shadow-soft"
                >
                  <p className="font-display text-3xl font-bold text-brand-700 mb-1">{stat.value}</p>
                  <p className="text-sm font-medium text-slate-600">{stat.label}</p>
                </motion.div>
              ))}
            </motion.div>
          </motion.div>
        </section>

        {/* Footer */}
        <motion.footer
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
          className="border-t border-blue-100/40 bg-gradient-to-r from-white/60 via-slate-50/50 to-blue-50/40 backdrop-blur-xl"
        >
          <div className="mx-auto max-w-7xl px-6 py-8 md:px-8 text-center">
            <p className="text-sm text-slate-600">
              © 2026 VISIONATTEND. AI-powered attendance management system. All rights reserved.
            </p>
            <div className="flex justify-center gap-6 mt-4">
              <button className="text-xs text-slate-500 hover:text-slate-900 transition cursor-pointer">
                Privacy Policy
              </button>
              <button className="text-xs text-slate-500 hover:text-slate-900 transition cursor-pointer">
                Terms of Service
              </button>
              <button className="text-xs text-slate-500 hover:text-slate-900 transition cursor-pointer">
                Contact Us
              </button>
            </div>
          </div>
        </motion.footer>
      </div>
    </div>
  )
}
