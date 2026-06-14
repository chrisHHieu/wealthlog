'use client'

import { ArrowUp, Square } from 'lucide-react'
import { useEffect, useRef, useState, useCallback } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { cn } from '@/lib/utils'

interface Props {
  onSend: (message: string) => void
  /** Abort the in-flight run (shown as a Stop button while streaming). */
  onStop?: () => void
  streaming?: boolean
  /** Optional control rendered in a footer row inside the composer (e.g. model picker).
      When set, the composer switches to a stacked layout: textarea on top, footer below. */
  accessory?: React.ReactNode
}

export function ChatInput({ onSend, onStop, streaming, accessory }: Props) {
  const [value, setValue] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // Give focus back when an answer finishes so the user can type right away
  const prevStreamingRef = useRef(streaming)
  useEffect(() => {
    if (prevStreamingRef.current && !streaming) textareaRef.current?.focus()
    prevStreamingRef.current = streaming
  }, [streaming])

  const handleResize = useCallback(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 120) + 'px'
  }, [])

  const handleSend = () => {
    const trimmed = value.trim()
    if (!trimmed || streaming) return
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
      <div className={cn('chat-input-row', accessory && 'chat-input-row--stacked', streaming && 'streaming')}>
        <textarea
          ref={textareaRef}
          className="chat-textarea"
          placeholder={streaming ? 'Answering… type your next question' : 'Ask about your finances...'}
          value={value}
          onChange={(e) => { setValue(e.target.value); handleResize() }}
          onKeyDown={handleKeyDown}
          rows={1}
          autoFocus
        />
        {accessory ? (
          <div className="chat-input-footer">
            {accessory}
            <SendButton streaming={streaming} value={value} onSend={handleSend} onStop={onStop} />
          </div>
        ) : (
          <SendButton streaming={streaming} value={value} onSend={handleSend} onStop={onStop} />
        )}
      </div>
    </div>
  )
}

function SendButton({ streaming, value, onSend, onStop }: {
  streaming?: boolean
  value: string
  onSend: () => void
  onStop?: () => void
}) {
  return (
    <AnimatePresence mode="wait" initial={false}>
      {streaming ? (
        <motion.button
          key="stop"
          className="chat-send-btn chat-send-btn--stop"
          onClick={onStop}
          title="Stop generating"
          initial={{ scale: 0.6, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.6, opacity: 0 }}
          transition={{ duration: 0.15 }}
          whileTap={{ scale: 0.92 }}
        >
          <Square size={13} fill="currentColor" />
        </motion.button>
      ) : (
        <motion.button
          key="send"
          className="chat-send-btn"
          onClick={onSend}
          disabled={!value.trim()}
          initial={{ scale: 0.6, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.6, opacity: 0 }}
          transition={{ duration: 0.15 }}
          whileHover={{ scale: 1.08 }}
          whileTap={{ scale: 0.92 }}
        >
          <ArrowUp size={17} strokeWidth={2.4} />
        </motion.button>
      )}
    </AnimatePresence>
  )
}
