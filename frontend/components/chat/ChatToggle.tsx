'use client'

import { motion, AnimatePresence } from 'framer-motion'
import { MessageCircle, X } from 'lucide-react'
import { useAppStore } from '@/store/useAppStore'

export function ChatToggle() {
  const { chatOpen, toggleChat } = useAppStore()

  return (
    <motion.button
      className="chat-toggle"
      onClick={toggleChat}
      whileHover={{ scale: 1.08 }}
      whileTap={{ scale: 0.92 }}
      aria-label={chatOpen ? 'Đóng chat' : 'Mở trợ lý AI'}
      title="Trợ lý AI (Ctrl+/)"
    >
      <AnimatePresence mode="wait" initial={false}>
        {chatOpen ? (
          <motion.div
            key="close"
            initial={{ rotate: -90, opacity: 0 }}
            animate={{ rotate: 0, opacity: 1 }}
            exit={{ rotate: 90, opacity: 0 }}
            transition={{ duration: 0.2 }}
            style={{ display: 'flex' }}
          >
            <X size={22} strokeWidth={2.5} />
          </motion.div>
        ) : (
          <motion.div
            key="open"
            initial={{ rotate: 90, opacity: 0 }}
            animate={{ rotate: 0, opacity: 1 }}
            exit={{ rotate: -90, opacity: 0 }}
            transition={{ duration: 0.2 }}
            style={{ display: 'flex' }}
          >
            <MessageCircle size={22} strokeWidth={2.5} />
          </motion.div>
        )}
      </AnimatePresence>
    </motion.button>
  )
}
