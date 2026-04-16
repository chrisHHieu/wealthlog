'use client'

import { Plus } from 'lucide-react'
import { motion } from 'framer-motion'
import { useAppStore } from '@/store/useAppStore'

export function FAB() {
  const openAddTransaction = useAppStore(s => s.openAddTransaction)

  return (
    <motion.button
      id="fab-add-transaction"
      className="fab"
      onClick={() => openAddTransaction()}
      whileHover={{ scale: 1.08 }}
      whileTap={{ scale: 0.95 }}
      aria-label="Thêm giao dịch mới"
      title="Thêm giao dịch (N)"
    >
      <Plus size={22} strokeWidth={2.5} />
    </motion.button>
  )
}
