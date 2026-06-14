'use client'

import { useRef, useEffect, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import Image from 'next/image'
import { Plus, Trash2, ChevronDown, BarChart3, Wallet, TrendingUp, Target, ArrowDown, ArrowRight } from 'lucide-react'
import { ChatMessage } from '@/components/chat/ChatMessage'
import { ChatInput } from '@/components/chat/ChatInput'
import { useChat, useSessions, useModel } from '@/hooks/useChatState'
import { getGreeting, timeAgo } from '@/lib/utils'

const SUGGESTIONS = [
  { icon: BarChart3,  label: 'Financial overview this month', color: 'purple' },
  { icon: Wallet,     label: 'How much budget is left?',      color: 'blue'   },
  { icon: TrendingUp, label: 'Top spending items',         color: 'green'  },
  { icon: Target,     label: 'Savings goal progress',    color: 'gold'   },
] as const

/** Bucket sessions ChatGPT-style: Today / Yesterday / Previous 7 days / Older. */
function groupSessionsByDate<T extends { updatedAt: string }>(sessions: T[]) {
  const startOfDay = (d: Date) => new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime()
  const today = startOfDay(new Date())
  const day = 86_400_000
  const groups: { label: string; items: T[] }[] = [
    { label: 'Today', items: [] },
    { label: 'Yesterday', items: [] },
    { label: 'Previous 7 days', items: [] },
    { label: 'Older', items: [] },
  ]
  for (const s of sessions) {
    const t = startOfDay(new Date(s.updatedAt))
    if (t >= today) groups[0].items.push(s)
    else if (t >= today - day) groups[1].items.push(s)
    else if (t >= today - 7 * day) groups[2].items.push(s)
    else groups[3].items.push(s)
  }
  return groups.filter(g => g.items.length > 0)
}

export default function ChatPage() {
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const scrollContainerRef = useRef<HTMLDivElement>(null)
  const [isAutoScrollEnabled, setIsAutoScrollEnabled] = useState(true)
  const autoScrollRef = useRef(isAutoScrollEnabled)
  autoScrollRef.current = isAutoScrollEnabled
  const isSmoothScrollingRef = useRef(false)

  const { models, selectedModel, selectModel } = useModel()
  const { messages, isStreaming, sessionId, sendMessage, stopStreaming, retryLast, newSession, loadSession } = useChat(selectedModel)
  const { sessions, deleteSession } = useSessions(sessionId)
  const [showModelPicker, setShowModelPicker] = useState(false)
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null)

  // Keep activeSessionId in sync when sessionId changes (e.g. after sending first message)
  useEffect(() => { setActiveSessionId(sessionId) }, [sessionId])

  const handleScroll = () => {
    if (!scrollContainerRef.current || isSmoothScrollingRef.current) return
    const { scrollTop, scrollHeight, clientHeight } = scrollContainerRef.current
    const isAtBottom = scrollHeight - scrollTop - clientHeight < 100
    if (isAutoScrollEnabled !== isAtBottom) setIsAutoScrollEnabled(isAtBottom)
  }

  const scrollToBottomSmooth = () => {
    isSmoothScrollingRef.current = true
    setIsAutoScrollEnabled(true)
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    setTimeout(() => { isSmoothScrollingRef.current = false }, 800)
  }

  useEffect(() => {
    if (autoScrollRef.current && !isSmoothScrollingRef.current) {
      messagesEndRef.current?.scrollIntoView()
    }
  }, [messages])

  useEffect(() => {
    if (!showModelPicker) return
    const close = (e: MouseEvent) => {
      if (!(e.target as HTMLElement).closest('.chat-model-picker')) setShowModelPicker(false)
    }
    document.addEventListener('mousedown', close)
    return () => document.removeEventListener('mousedown', close)
  }, [showModelPicker])

  // Model picker lives inside the composer (Claude/ChatGPT style), so the
  // dropdown opens upward from the input footer.
  const modelPicker = models.length > 0 ? (
    <div className="chat-model-picker chat-model-picker--composer">
      <button className="chat-modelbar-btn" onClick={() => setShowModelPicker(v => !v)}>
        <span className={`chat-modelbar-dot${isStreaming ? ' streaming' : ''}`} />
        <span className="chat-modelbar-name">
          {models.find(m => m.id === selectedModel)?.name ?? selectedModel}
        </span>
        <ChevronDown size={13} />
      </button>
      <AnimatePresence>
        {showModelPicker && (
          <motion.div
            className="chat-model-dropdown"
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 6 }}
            transition={{ duration: 0.15 }}
          >
            {models.map(m => (
              <button
                key={m.id}
                className={`chat-model-option${m.id === selectedModel ? ' active' : ''}`}
                onClick={() => { selectModel(m.id); setShowModelPicker(false) }}
              >
                <span className="chat-model-option-name">{m.name}</span>
                <span className="chat-model-option-desc">{m.description}</span>
              </button>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  ) : null

  return (
    <div className="chat-page">
      {/* ── Left: Session History ── */}
      <aside className="chat-page-sidebar">
        <div className="chat-page-sidebar-header">
          <button
            className={`chat-page-new-btn${activeSessionId === null ? ' active' : ''}`}
            onClick={() => { setActiveSessionId(null); newSession() }}
          >
            <Plus size={15} />
            <span>New conversation</span>
          </button>
        </div>
        <div className="chat-page-session-list">
          {sessions.length === 0 ? (
            <p className="chat-page-session-empty">No conversations yet.</p>
          ) : (
            groupSessionsByDate(sessions).map(group => (
              <div key={group.label}>
                <div className="chat-page-session-group">{group.label}</div>
                {group.items.map(s => (
                  <div
                    key={s.id}
                    className={`chat-page-session-item${s.id === activeSessionId ? ' active' : ''}`}
                    onClick={() => { setActiveSessionId(s.id); loadSession(s.id) }}
                  >
                    <div className="chat-page-session-info">
                      <span className="chat-page-session-title">{s.title}</span>
                      <span className="chat-page-session-meta">{timeAgo(s.updatedAt)} · {s.messageCount} {s.messageCount === 1 ? 'message' : 'messages'}</span>
                    </div>
                    <button
                      className="chat-page-session-delete"
                      onClick={e => { e.stopPropagation(); deleteSession(s.id) }}
                      title="Delete"
                    >
                      <Trash2 size={12} />
                    </button>
                  </div>
                ))}
              </div>
            ))
          )}
        </div>
      </aside>

      {/* ── Right: Conversation ── */}
      <div className="chat-page-main">
        {/* Messages */}
        <div className="chat-page-messages" ref={scrollContainerRef} onScroll={handleScroll}>
          {messages.length === 0 ? (
            <div className="chat-page-empty">
              <div className="chat-page-hero">
                <div style={{ width: 112, height: 112, position: 'relative', flexShrink: 0 }}>
                  <Image
                    src="/images/ai-avatar.png"
                    alt="Expensep"
                    fill
                    style={{ objectFit: 'contain' }}
                  />
                </div>
                <h1 className="chat-page-hero-title">{getGreeting()} — how can I help?</h1>
                <p className="chat-empty-sub" style={{ maxWidth: 340 }}>
                  Analyze spending, check budgets, track goals, and more.
                </p>
              </div>
              <div className="chat-hero-suggestions">
                {SUGGESTIONS.map(({ icon: Icon, label, color }) => (
                  <button key={label} className="chat-hero-suggest-row" onClick={() => sendMessage(label)}>
                    <div className={`chat-suggest-icon ${color}`}><Icon size={14} /></div>
                    <span>{label}</span>
                    <ArrowRight size={14} className="chat-hero-suggest-arrow" />
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="chat-page-messages-inner">
              {messages.map(msg => <ChatMessage key={msg.id} message={msg} onRetry={retryLast} />)}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        <div style={{ position: 'relative', height: 0, zIndex: 50, display: 'flex', justifyContent: 'center' }}>
          <AnimatePresence>
            {!isAutoScrollEnabled && messages.length > 0 && (
              <motion.button
                className="chat-scroll-bottom-btn"
                style={{ position: 'absolute', bottom: 16 }}
                initial={{ opacity: 0, scale: 0.8, y: 10 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.8, y: 10 }}
                onClick={scrollToBottomSmooth}
              >
                {isStreaming ? (
                  <div className="chat-inline-dots" style={{ transform: 'scale(0.8)' }}>
                    <span /><span /><span />
                  </div>
                ) : (
                  <ArrowDown size={16} />
                )}
              </motion.button>
            )}
          </AnimatePresence>
        </div>

        {/* Input */}
        <div className="chat-page-input-wrap">
          <div className="chat-page-input-inner">
            <ChatInput
              onSend={(msg) => { scrollToBottomSmooth(); sendMessage(msg) }}
              onStop={stopStreaming}
              streaming={isStreaming}
              accessory={modelPicker}
            />
            <div className="chat-composer-hint">Enter to send · Shift+Enter for a new line</div>
          </div>
        </div>
      </div>
    </div>
  )
}
