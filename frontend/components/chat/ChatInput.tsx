'use client'

import { Send } from 'lucide-react'
import { useRef, useState, useCallback } from 'react'
import { motion } from 'framer-motion'

const SUGGESTIONS = [
  'Tổng quan tài chính tháng này',
  'Ngân sách còn bao nhiêu?',
  'Top chi tiêu lớn nhất',
  'Tài sản ròng hiện tại',
]

interface Props {
  onSend: (message: string) => void
  disabled?: boolean
}

export function ChatInput({ onSend, disabled }: Props) {
  const [value, setValue] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const handleResize = useCallback(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 120) + 'px'
  }, [])

  const handleSend = () => {
    const trimmed = value.trim()
    if (!trimmed || disabled) return
    onSend(trimmed)
    setValue('')
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="chat-input-area">
      {/* Suggestion chips — only show when empty */}
      {!value && !disabled && (
        <div className="chat-suggestions">
          {SUGGESTIONS.map((s) => (
            <motion.button
              key={s}
              className="chat-chip"
              onClick={() => onSend(s)}
              whileHover={{ scale: 1.03 }}
              whileTap={{ scale: 0.97 }}
            >
              {s}
            </motion.button>
          ))}
        </div>
      )}

      <div className="chat-input-row">
        <textarea
          ref={textareaRef}
          className="chat-textarea"
          placeholder="Hỏi về tài chính của bạn..."
          value={value}
          onChange={(e) => { setValue(e.target.value); handleResize() }}
          onKeyDown={handleKeyDown}
          rows={1}
          disabled={disabled}
        />
        <motion.button
          className="chat-send-btn"
          onClick={handleSend}
          disabled={!value.trim() || disabled}
          whileHover={{ scale: 1.08 }}
          whileTap={{ scale: 0.92 }}
        >
          <Send size={16} />
        </motion.button>
      </div>
    </div>
  )
}
