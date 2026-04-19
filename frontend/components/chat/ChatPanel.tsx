'use client'

import { motion, AnimatePresence } from 'framer-motion'
import { Sparkles, Trash2, X, BarChart3, Wallet, TrendingUp, Target, Plus, MessageSquare, ChevronLeft } from 'lucide-react'
import { useRef, useEffect, useState, useCallback } from 'react'
import { useAppStore } from '@/store/useAppStore'
import { API_URL } from '@/lib/api'
import { ChatMessage } from './ChatMessage'
import { ChatInput } from './ChatInput'
import type { ChatMessage as ChatMessageType, ChatSession, ChatStep } from '@/types/chat'

type PersistedBlock = {
  type?: string
  text?: string
  thinking?: string
  id?: string
  name?: string
  input?: Record<string, unknown>
  tool_use_id?: string
  content?: unknown
}

type PersistedMessage = {
  id: string
  role: 'user' | 'assistant'
  content: string
  blocks?: PersistedBlock[] | null
  createdAt: string
}

function isToolResultOnlyRow(m: PersistedMessage): boolean {
  return !!m.blocks && m.blocks.length > 0 && m.blocks.every(b => b?.type === 'tool_result')
}

function toolResultText(content: unknown): string {
  if (typeof content === 'string') return content
  try { return JSON.stringify(content) } catch { return String(content) }
}

/**
 * Convert persisted DB rows into UI ChatMessages, rebuilding the thinking/tool
 * timeline. Consecutive assistant iterations (thinking → tool_use → tool_result
 * → more thinking → final text) are merged into a single UI message so the
 * reloaded view matches how it looked while streaming.
 */
function rowsToChatMessages(rows: PersistedMessage[]): ChatMessageType[] {
  // tool_use_id → result text (results are stored in separate "user" rows)
  const resultByToolUseId = new Map<string, string>()
  for (const m of rows) {
    if (!m.blocks) continue
    for (const b of m.blocks) {
      if (b?.type === 'tool_result' && typeof b.tool_use_id === 'string') {
        resultByToolUseId.set(b.tool_use_id, toolResultText(b.content))
      }
    }
  }

  const out: ChatMessageType[] = []
  let currentAssistant: ChatMessageType | null = null

  for (const m of rows) {
    if (m.role === 'user' && !isToolResultOnlyRow(m)) {
      out.push({
        id: m.id,
        role: 'user',
        content: m.content,
        timestamp: new Date(m.createdAt),
      })
      currentAssistant = null
      continue
    }

    if (m.role === 'assistant') {
      if (!currentAssistant) {
        currentAssistant = {
          id: m.id,
          role: 'assistant',
          content: '',
          timestamp: new Date(m.createdAt),
          steps: [],
        }
        out.push(currentAssistant)
      }

      const blocks = m.blocks || []
      if (blocks.length === 0 && m.content) {
        // Legacy row without blocks — render as a single text step
        currentAssistant.steps!.push({
          kind: 'text',
          stepId: m.id,
          content: m.content,
        })
        currentAssistant.content += m.content
        continue
      }

      blocks.forEach((b, i) => {
        const stepId = `${m.id}-${i}`
        if (b?.type === 'thinking') {
          currentAssistant!.steps!.push({
            kind: 'thinking',
            stepId,
            content: b.thinking || '',
          })
        } else if (b?.type === 'text' && b.text) {
          currentAssistant!.steps!.push({
            kind: 'text',
            stepId,
            content: b.text,
          })
          currentAssistant!.content += b.text
        } else if (b?.type === 'tool_use' && typeof b.id === 'string') {
          const step: ChatStep = {
            kind: 'tool',
            stepId,
            id: b.id,
            name: b.name || '',
            input: b.input,
            result: resultByToolUseId.get(b.id),
            status: 'done',
          }
          currentAssistant!.steps!.push(step)
        }
      })
    }
    // tool_result-only user rows: skip (already folded into tool steps via the map)
  }

  return out
}

const SUGGESTIONS = [
  { icon: BarChart3, label: 'Tổng quan tài chính tháng này', color: 'purple' },
  { icon: Wallet,    label: 'Ngân sách còn bao nhiêu?',      color: 'blue'   },
  { icon: TrendingUp,label: 'Top chi tiêu lớn nhất',         color: 'green'  },
  { icon: Target,    label: 'Tiến độ mục tiêu tiết kiệm',    color: 'gold'   },
] as const

function useChat() {
  const [messages, setMessages] = useState<ChatMessageType[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const abortRef = useRef<AbortController | null>(null)

  const loadSession = useCallback(async (id: string) => {
    try {
      const res = await fetch(`${API_URL}/api/chat/sessions/${id}`)
      if (!res.ok) return
      const data = await res.json()
      setSessionId(id)
      setMessages(rowsToChatMessages(data.messages as PersistedMessage[]))
    } catch {
      // ignore
    }
  }, [])

  const sendMessage = useCallback(async (content: string) => {
    const userMsg: ChatMessageType = {
      id: crypto.randomUUID(),
      role: 'user',
      content,
      timestamp: new Date(),
    }
    const aiId = crypto.randomUUID()

    setMessages(prev => [...prev, userMsg, {
      id: aiId,
      role: 'assistant',
      content: '',
      timestamp: new Date(),
      steps: [],
      isStreaming: true,
    }])
    setIsStreaming(true)

    // Build message history for API (only role + content)
    const history = [...messages, userMsg].map(m => ({
      role: m.role,
      content: m.content,
    }))

    const abort = new AbortController()
    abortRef.current = abort

    try {
      const res = await fetch(`${API_URL}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sessionId: sessionId,
          messages: history,
        }),
        signal: abort.signal,
      })

      if (!res.ok || !res.body) {
        throw new Error(`API error: ${res.status}`)
      }

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        let eventType = ''
        for (const line of lines) {
          if (line.startsWith('event: ')) {
            eventType = line.slice(7).trim()
          } else if (line.startsWith('data: ') && eventType) {
            const data = JSON.parse(line.slice(6))

            if (eventType === 'session') {
              setSessionId(data.session_id)
            } else if (eventType === 'thinking_start') {
              setMessages(prev => prev.map(m =>
                m.id === aiId
                  ? { ...m, steps: [...(m.steps || []), {
                      kind: 'thinking' as const,
                      stepId: data.step_id,
                      content: '',
                      streaming: true,
                    }] }
                  : m
              ))
            } else if (eventType === 'thinking_delta') {
              setMessages(prev => prev.map(m =>
                m.id === aiId
                  ? { ...m, steps: (m.steps || []).map(s =>
                      s.kind === 'thinking' && s.stepId === data.step_id
                        ? { ...s, content: s.content + data.text }
                        : s
                    ) }
                  : m
              ))
            } else if (eventType === 'thinking_stop') {
              setMessages(prev => prev.map(m =>
                m.id === aiId
                  ? { ...m, steps: (m.steps || []).map(s =>
                      s.kind === 'thinking' && s.stepId === data.step_id
                        ? { ...s, streaming: false }
                        : s
                    ) }
                  : m
              ))
            } else if (eventType === 'text_start') {
              setMessages(prev => prev.map(m =>
                m.id === aiId
                  ? { ...m, steps: [...(m.steps || []), {
                      kind: 'text' as const,
                      stepId: data.step_id,
                      content: '',
                      streaming: true,
                    }] }
                  : m
              ))
            } else if (eventType === 'text_delta') {
              setMessages(prev => prev.map(m => {
                if (m.id !== aiId) return m
                const steps = m.steps || []
                // Append to existing text step, or create one if missing (safety)
                const hasStep = steps.some(s => s.kind === 'text' && s.stepId === data.step_id)
                const nextSteps = hasStep
                  ? steps.map(s =>
                      s.kind === 'text' && s.stepId === data.step_id
                        ? { ...s, content: s.content + data.text }
                        : s
                    )
                  : [...steps, { kind: 'text' as const, stepId: data.step_id, content: data.text, streaming: true }]
                return { ...m, steps: nextSteps, content: m.content + data.text }
              }))
            } else if (eventType === 'text_stop') {
              setMessages(prev => prev.map(m =>
                m.id === aiId
                  ? { ...m, steps: (m.steps || []).map(s =>
                      s.kind === 'text' && s.stepId === data.step_id
                        ? { ...s, streaming: false }
                        : s
                    ) }
                  : m
              ))
            } else if (eventType === 'tool_start') {
              setMessages(prev => prev.map(m =>
                m.id === aiId
                  ? { ...m, steps: [...(m.steps || []), {
                      kind: 'tool' as const,
                      stepId: data.step_id,
                      id: data.id,
                      name: data.name,
                      status: 'running' as const,
                    }] }
                  : m
              ))
            } else if (eventType === 'tool_input') {
              setMessages(prev => prev.map(m =>
                m.id === aiId
                  ? { ...m, steps: (m.steps || []).map(s =>
                      s.kind === 'tool' && s.id === data.id
                        ? { ...s, input: data.input }
                        : s
                    ) }
                  : m
              ))
            } else if (eventType === 'tool_done') {
              setMessages(prev => prev.map(m =>
                m.id === aiId
                  ? { ...m, steps: (m.steps || []).map(s =>
                      s.kind === 'tool' && s.id === data.id
                        ? { ...s, status: 'done' as const, result: data.result }
                        : s
                    ) }
                  : m
              ))
            } else if (eventType === 'done') {
              setMessages(prev => prev.map(m => {
                if (m.id !== aiId) return m
                // Mark the LAST text step as the final answer
                const steps = m.steps || []
                let lastTextIdx = -1
                for (let i = steps.length - 1; i >= 0; i--) {
                  if (steps[i].kind === 'text') { lastTextIdx = i; break }
                }
                const nextSteps = steps.map((s, i) =>
                  i === lastTextIdx && s.kind === 'text'
                    ? { ...s, final: true, streaming: false }
                    : s
                )
                return { ...m, steps: nextSteps, isStreaming: false }
              }))
            }

            eventType = ''
          }
        }
      }
    } catch (err) {
      if ((err as Error).name !== 'AbortError') {
        setMessages(prev => prev.map(m =>
          m.id === aiId
            ? { ...m, content: m.content || 'Xin lỗi, đã có lỗi xảy ra. Vui lòng thử lại.', isStreaming: false }
            : m
        ))
      }
    } finally {
      setIsStreaming(false)
      abortRef.current = null
    }
  }, [messages, sessionId])

  const newSession = useCallback(() => {
    abortRef.current?.abort()
    setMessages([])
    setSessionId(null)
    setIsStreaming(false)
  }, [])

  return { messages, isStreaming, sessionId, sendMessage, newSession, loadSession }
}

function useSessions(currentSessionId: string | null) {
  const [sessions, setSessions] = useState<ChatSession[]>([])
  const [loading, setLoading] = useState(false)

  const fetchSessions = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetch(`${API_URL}/api/chat/sessions`)
      if (res.ok) {
        setSessions(await res.json())
      }
    } catch {
      // ignore
    } finally {
      setLoading(false)
    }
  }, [])

  const deleteSession = useCallback(async (id: string) => {
    try {
      await fetch(`${API_URL}/api/chat/sessions/${id}`, { method: 'DELETE' })
      setSessions(prev => prev.filter(s => s.id !== id))
    } catch {
      // ignore
    }
  }, [])

  // Refresh sessions list when currentSessionId changes (new messages saved)
  useEffect(() => {
    fetchSessions()
  }, [fetchSessions, currentSessionId])

  return { sessions, loading, fetchSessions, deleteSession }
}

export function ChatPanel() {
  const { chatOpen, closeChat } = useAppStore()
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const { messages, isStreaming, sessionId, sendMessage, newSession, loadSession } = useChat()
  const { sessions, deleteSession } = useSessions(sessionId)
  const [showHistory, setShowHistory] = useState(false)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSelectSession = (id: string) => {
    loadSession(id)
    setShowHistory(false)
  }

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
                <div className="chat-header-icon">
                  <Sparkles size={14} />
                </div>
              )}
              <h3>{showHistory ? 'Lịch sử' : 'WealthLog AI'}</h3>
            </div>
            <div className="chat-header-actions">
              {!showHistory && (
                <>
                  <button
                    className="chat-header-btn"
                    onClick={() => setShowHistory(true)}
                    title="Lịch sử trò chuyện"
                  >
                    <MessageSquare size={14} />
                  </button>
                  <button className="chat-header-btn" onClick={newSession} title="Cuộc trò chuyện mới">
                    <Plus size={14} />
                  </button>
                </>
              )}
              <button className="chat-header-btn" onClick={closeChat} title="Đóng (Ctrl+/)">
                <X size={14} />
              </button>
            </div>
          </div>

          {showHistory ? (
            /* ── Session History List ── */
            <div className="chat-messages">
              {sessions.length === 0 ? (
                <div className="chat-empty-history">
                  <p>Chưa có cuộc trò chuyện nào.</p>
                </div>
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
                        <span className="chat-session-meta">
                          {s.messageCount} tin nhắn
                        </span>
                      </div>
                      <button
                        className="chat-session-delete"
                        onClick={(e) => {
                          e.stopPropagation()
                          deleteSession(s.id)
                        }}
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
            /* ── Chat Messages ── */
            <>
              <div className="chat-messages">
                {messages.length === 0 && (
                  <div className="chat-empty">
                    <div className="chat-empty-hero">
                      <div className="chat-empty-logo">
                        <Sparkles size={22} />
                      </div>
                      <p className="chat-empty-greeting">Tôi có thể giúp gì?</p>
                      <p className="chat-empty-sub">Phân tích chi tiêu, kiểm tra ngân sách, theo dõi mục tiêu và hơn thế nữa.</p>
                    </div>

                    <div className="chat-empty-suggestions">
                      {SUGGESTIONS.map(({ icon: Icon, label, color }) => (
                        <button
                          key={label}
                          className="chat-suggest-card"
                          onClick={() => sendMessage(label)}
                        >
                          <div className={`chat-suggest-icon ${color}`}>
                            <Icon size={14} />
                          </div>
                          <span className="chat-suggest-label">{label}</span>
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {messages.map((msg) => (
                  <ChatMessage key={msg.id} message={msg} />
                ))}

                <div ref={messagesEndRef} />
              </div>

              {/* Input */}
              <ChatInput onSend={sendMessage} disabled={isStreaming} />
            </>
          )}
        </motion.div>
      )}
    </AnimatePresence>
  )
}
