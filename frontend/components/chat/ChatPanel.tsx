'use client'

import { motion, AnimatePresence } from 'framer-motion'
import {
  Sparkles, Trash2, X, BarChart3, Wallet, TrendingUp, Target,
  Plus, MessageSquare, ChevronLeft, ChevronDown, Maximize2, ArrowDown
} from 'lucide-react'
import { useRef, useEffect, useState } from 'react'
import Image from 'next/image'
import { useRouter } from 'next/navigation'
import { useAppStore } from '@/store/useAppStore'
import { ChatMessage } from './ChatMessage'
import { ChatInput } from './ChatInput'
import { useChat, useSessions, useModel } from '@/hooks/useChatState'

const SUGGESTIONS = [
  { icon: BarChart3,  label: 'Tổng quan tài chính tháng này', color: 'purple' },
  { icon: Wallet,     label: 'Ngân sách còn bao nhiêu?',      color: 'blue'   },
  { icon: TrendingUp, label: 'Top chi tiêu lớn nhất',         color: 'green'  },
  { icon: Target,     label: 'Tiến độ mục tiêu tiết kiệm',    color: 'gold'   },
] as const

export function ChatPanel() {
  const { chatOpen, closeChat } = useAppStore()
  const router = useRouter()
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const { models, selectedModel, selectModel } = useModel()
  const { messages, isStreaming, sessionId, sendMessage, newSession, loadSession } = useChat(selectedModel)
  const { sessions, deleteSession } = useSessions(sessionId)
  const [showHistory, setShowHistory] = useState(false)
  const [showModelPicker, setShowModelPicker] = useState(false)
  
  const scrollContainerRef = useRef<HTMLDivElement>(null)
  const [isAutoScrollEnabled, setIsAutoScrollEnabled] = useState(true)
  const autoScrollRef = useRef(isAutoScrollEnabled)
  autoScrollRef.current = isAutoScrollEnabled
  const isSmoothScrollingRef = useRef(false)

  const handleScroll = () => {
    if (!scrollContainerRef.current || isSmoothScrollingRef.current) return
    const { scrollTop, scrollHeight, clientHeight } = scrollContainerRef.current
    const isAtBottom = scrollHeight - scrollTop - clientHeight < 100
    if (isAutoScrollEnabled !== isAtBottom) {
      setIsAutoScrollEnabled(isAtBottom)
    }
  }

  const scrollToBottomSmooth = () => {
    isSmoothScrollingRef.current = true
    setIsAutoScrollEnabled(true)
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    setTimeout(() => {
      isSmoothScrollingRef.current = false
    }, 800)
  }

  useEffect(() => {
    if (autoScrollRef.current && !isSmoothScrollingRef.current) {
      messagesEndRef.current?.scrollIntoView()
    }
  }, [messages])

  const handleSelectSession = (id: string) => {
    loadSession(id)
    setShowHistory(false)
  }

  const handleExpand = () => {
    closeChat()
    router.push('/chat')
  }

  useEffect(() => {
    if (!showModelPicker) return
    const close = (e: MouseEvent) => {
      if (!(e.target as HTMLElement).closest('.chat-model-picker')) setShowModelPicker(false)
    }
    document.addEventListener('mousedown', close)
    return () => document.removeEventListener('mousedown', close)
  }, [showModelPicker])

  return (
    <AnimatePresence>
      {chatOpen && (
        <motion.div
          className="chat-panel"
          initial={{ x: '100%' }}
          animate={{ x: 0 }}
          exit={{ x: '100%' }}
          transition={{ duration: 0.28, ease: [0.4, 0, 0.2, 1] }}
        >
          {/* Header */}
          <div className="chat-header">
            <div className="chat-header-left">
              {showHistory ? (
                <button className="chat-header-btn" onClick={() => setShowHistory(false)}>
                  <ChevronLeft size={16} />
                </button>
              ) : (
                <div className="chat-header-icon"><Sparkles size={14} /></div>
              )}
              <h3>{showHistory ? 'Lịch sử' : 'Chip'}</h3>
              {!showHistory && models.length > 0 && (
                <div className="chat-model-picker">
                  <button className="chat-model-btn" onClick={() => setShowModelPicker(v => !v)}>
                    <span>{models.find(m => m.id === selectedModel)?.name ?? selectedModel}</span>
                    <ChevronDown size={11} />
                  </button>
                  <AnimatePresence>
                    {showModelPicker && (
                      <motion.div
                        className="chat-model-dropdown"
                        initial={{ opacity: 0, y: -6 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -6 }}
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
              )}
            </div>
            <div className="chat-header-actions">
              {!showHistory && (
                <>
                  <button className="chat-header-btn" onClick={() => setShowHistory(true)} title="Lịch sử trò chuyện">
                    <MessageSquare size={14} />
                  </button>
                  <button className="chat-header-btn" onClick={newSession} title="Cuộc trò chuyện mới">
                    <Plus size={14} />
                  </button>
                  <button className="chat-header-btn" onClick={handleExpand} title="Mở rộng toàn trang">
                    <Maximize2 size={14} />
                  </button>
                </>
              )}
              <button className="chat-header-btn" onClick={closeChat} title="Đóng (Ctrl+/)">
                <X size={14} />
              </button>
            </div>
          </div>

          {showHistory ? (
            <div className="chat-messages">
              {sessions.length === 0 ? (
                <div className="chat-empty-history"><p>Chưa có cuộc trò chuyện nào.</p></div>
              ) : (
                <div className="chat-session-list">
                  {sessions.map(s => (
                    <div
                      key={s.id}
                      className={`chat-session-item ${s.id === sessionId ? 'active' : ''}`}
                      onClick={() => handleSelectSession(s.id)}
                    >
                      <div className="chat-session-info">
                        <span className="chat-session-title">{s.title}</span>
                        <span className="chat-session-meta">{s.messageCount} tin nhắn</span>
                      </div>
                      <button
                        className="chat-session-delete"
                        onClick={e => { e.stopPropagation(); deleteSession(s.id) }}
                        title="Xóa"
                      >
                        <Trash2 size={12} />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <>
              <div className="chat-messages" ref={scrollContainerRef} onScroll={handleScroll}>
                {messages.length === 0 && (
                  <div className="chat-empty">
                    <div className="chat-empty-hero">
                      <div className="chat-empty-logo"><Image src="/images/ai-avatar.png" alt="Chip" fill style={{ objectFit: 'contain' }} /></div>
                      <p className="chat-empty-greeting">Tôi có thể giúp gì?</p>
                      <p className="chat-empty-sub">Phân tích chi tiêu, kiểm tra ngân sách, theo dõi mục tiêu và hơn thế nữa.</p>
                    </div>
                    <div className="chat-empty-suggestions">
                      {SUGGESTIONS.map(({ icon: Icon, label, color }) => (
                        <button key={label} className="chat-suggest-card" onClick={() => sendMessage(label)}>
                          <div className={`chat-suggest-icon ${color}`}><Icon size={14} /></div>
                          <span className="chat-suggest-label">{label}</span>
                        </button>
                      ))}
                    </div>
                  </div>
                )}
                {messages.map(msg => <ChatMessage key={msg.id} message={msg} />)}
                <div ref={messagesEndRef} />
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
              <ChatInput onSend={(msg) => {
                scrollToBottomSmooth()
                sendMessage(msg)
              }} disabled={isStreaming} />
            </>
          )}
        </motion.div>
      )}
    </AnimatePresence>
  )
}
