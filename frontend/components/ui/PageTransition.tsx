'use client'

import { motion } from 'framer-motion'
import { ReactNode } from 'react'

interface PageTransitionProps {
  children: ReactNode
  className?: string
}

// Spring-based motion: content settles in with natural weight instead of a flat ease
const pageVariants = {
  hidden: { opacity: 0, y: 12 },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      type: 'spring' as const,
      stiffness: 260,
      damping: 30,
      mass: 0.9,
      staggerChildren: 0.06,
      delayChildren: 0.03,
    },
  },
}

const itemVariants = {
  hidden: { opacity: 0, y: 14 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { type: 'spring' as const, stiffness: 300, damping: 32, mass: 0.8 },
  },
}

export function PageTransition({ children, className }: PageTransitionProps) {
  return (
    <motion.div
      initial="hidden"
      animate="visible"
      variants={pageVariants}
      className={className}
    >
      {children}
    </motion.div>
  )
}

export function StaggerItem({ children, className }: PageTransitionProps) {
  return (
    <motion.div variants={itemVariants} className={className}>
      {children}
    </motion.div>
  )
}
