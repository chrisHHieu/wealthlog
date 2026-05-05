'use client'

import { useState, useCallback, useRef, useEffect } from 'react'
import { API_URL } from '@/lib/api'
import type { ChatMessage as ChatMessageType, ChatSession, ModelOption, ChatStep } from '@/types/chat'

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

export function rowsToChatMessages(rows: PersistedMessage[]): ChatMessageType[] {
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
      out.push({ id: m.id, role: 'user', content: m.content, timestamp: new Date(m.createdAt) })
      currentAssistant = null
      continue
    }

    if (m.role === 'assistant') {
      if (!currentAssistant) {
        currentAssistant = { id: m.id, role: 'assistant', content: '', timestamp: new Date(m.createdAt), steps: [] }
        out.push(currentAssistant)
      }

      const blocks = m.blocks || []
      if (blocks.length === 0 && m.content) {
        currentAssistant.steps!.push({ kind: 'text', stepId: m.id, content: m.content })
        currentAssistant.content += m.content
        continue
      }

      blocks.forEach((b, i) => {
        const stepId = `${m.id}-${i}`
        if (b?.type === 'thinking') {
          currentAssistant!.steps!.push({ kind: 'thinking', stepId, content: b.thinking || '' })
        } else if (b?.type === 'text' && b.text) {
          currentAssistant!.steps!.push({ kind: 'text', stepId, content: b.text })
          currentAssistant!.content += b.text
        } else if (b?.type === 'tool_use' && typeof b.id === 'string') {
          const step: ChatStep = {
            kind: 'tool', stepId, id: b.id, name: b.name || '',
            input: b.input, result: resultByToolUseId.get(b.id), status: 'done',
          }
          currentAssistant!.steps!.push(step)
        }
      })
    }
  }

  return out
}

export function useChat(model: string | null) {
  const [messages, setMessages] = useState<ChatMessageType[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const abortRef = useRef<AbortController | null>(null)

  // Mirror of `messages` so async callbacks (resumeStream's first-event hook)
  // can read the latest list synchronously without re-rendering on every change.
  const messagesRef = useRef(messages)
  messagesRef.current = messages

  // Apply a single SSE event to the assistant message identified by aiId.
  // Shared between live POST streaming and reconnect-resume GET streaming.
  const applyEvent = useCallback((eventType: string, data: Record<string, unknown>, aiId: string) => {
    if (eventType === 'session') {
      setSessionId(data.session_id as string)
    } else if (eventType === 'thinking_start') {
      setMessages(prev => prev.map(m => m.id !== aiId ? m : {
        ...m, steps: [...(m.steps || []), { kind: 'thinking' as const, stepId: data.step_id as string, content: '', streaming: true }],
      }))
    } else if (eventType === 'thinking_delta') {
      setMessages(prev => prev.map(m => m.id !== aiId ? m : {
        ...m, steps: (m.steps || []).map(s =>
          s.kind === 'thinking' && s.stepId === data.step_id ? { ...s, content: s.content + (data.text as string) } : s
        ),
      }))
    } else if (eventType === 'thinking_stop') {
      setMessages(prev => prev.map(m => m.id !== aiId ? m : {
        ...m, steps: (m.steps || []).map(s =>
          s.kind === 'thinking' && s.stepId === data.step_id ? { ...s, streaming: false } : s
        ),
      }))
    } else if (eventType === 'text_start') {
      setMessages(prev => prev.map(m => m.id !== aiId ? m : {
        ...m, steps: [...(m.steps || []), { kind: 'text' as const, stepId: data.step_id as string, content: '', streaming: true }],
      }))
    } else if (eventType === 'text_delta') {
      setMessages(prev => prev.map(m => {
        if (m.id !== aiId) return m
        const steps = m.steps || []
        const hasStep = steps.some(s => s.kind === 'text' && s.stepId === data.step_id)
        const nextSteps = hasStep
          ? steps.map(s => s.kind === 'text' && s.stepId === data.step_id ? { ...s, content: s.content + (data.text as string) } : s)
          : [...steps, { kind: 'text' as const, stepId: data.step_id as string, content: data.text as string, streaming: true }]
        return { ...m, steps: nextSteps, content: m.content + (data.text as string) }
      }))
    } else if (eventType === 'text_stop') {
      setMessages(prev => prev.map(m => m.id !== aiId ? m : {
        ...m, steps: (m.steps || []).map(s =>
          s.kind === 'text' && s.stepId === data.step_id ? { ...s, streaming: false } : s
        ),
      }))
    } else if (eventType === 'tool_start') {
      setMessages(prev => prev.map(m => m.id !== aiId ? m : {
        ...m, steps: [...(m.steps || []), { kind: 'tool' as const, stepId: data.step_id as string, id: data.id as string, name: data.name as string, status: 'running' as const }],
      }))
    } else if (eventType === 'tool_input') {
      setMessages(prev => prev.map(m => m.id !== aiId ? m : {
        ...m, steps: (m.steps || []).map(s =>
          s.kind === 'tool' && s.id === data.id ? { ...s, input: data.input as Record<string, unknown> } : s
        ),
      }))
    } else if (eventType === 'tool_done') {
      setMessages(prev => prev.map(m => m.id !== aiId ? m : {
        ...m, steps: (m.steps || []).map(s =>
          s.kind === 'tool' && s.id === data.id
            ? { ...s, status: data.is_error ? 'error' as const : 'done' as const, result: data.result as string }
            : s
        ),
      }))
    } else if (eventType === 'done') {
      setMessages(prev => prev.map(m => {
        if (m.id !== aiId) return m
        const steps = m.steps || []
        let lastTextIdx = -1
        for (let i = steps.length - 1; i >= 0; i--) {
          if (steps[i].kind === 'text') { lastTextIdx = i; break }
        }
        return {
          ...m,
          steps: steps.map((s, i) =>
            i === lastTextIdx && s.kind === 'text' ? { ...s, final: true, streaming: false } : s
          ),
          isStreaming: false,
        }
      }))
    }
  }, [])

  // Read SSE frames off a Response body until the stream closes. Each frame
  // is parsed and dispatched to applyEvent. aiId is read through a ref so
  // resumeStream can decide which assistant message to attach to AFTER seeing
  // the first event (it may need to bail if the server says no_active).
  const consumeStream = useCallback(async (
    res: Response,
    aiIdRef: { current: string },
    onFirstEvent?: (eventType: string, data: Record<string, unknown>) => boolean,
  ) => {
    if (!res.body) return
    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    let firstEventSeen = false

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
          if (!firstEventSeen) {
            firstEventSeen = true
            if (onFirstEvent && !onFirstEvent(eventType, data)) {
              await reader.cancel().catch(() => {})
              return
            }
          }
          applyEvent(eventType, data, aiIdRef.current)
          eventType = ''
        }
      }
    }
  }, [applyEvent])

  const sendMessage = useCallback(async (content: string) => {
    const userMsg: ChatMessageType = { id: crypto.randomUUID(), role: 'user', content, timestamp: new Date() }
    const aiId = crypto.randomUUID()

    setMessages(prev => [...prev, userMsg, {
      id: aiId, role: 'assistant', content: '', timestamp: new Date(), steps: [], isStreaming: true,
    }])
    setIsStreaming(true)

    const history = [...messages, userMsg].map(m => ({ role: m.role, content: m.content }))
    const abort = new AbortController()
    abortRef.current = abort

    try {
      const res = await fetch(`${API_URL}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sessionId, messages: history, ...(model ? { model } : {}) }),
        signal: abort.signal,
      })
      if (!res.ok || !res.body) throw new Error(`API error: ${res.status}`)
      await consumeStream(res, { current: aiId })
    } catch (err) {
      if ((err as Error).name !== 'AbortError') {
        setMessages(prev => prev.map(m =>
          m.id === aiId ? { ...m, content: m.content || 'Xin lỗi, đã có lỗi xảy ra. Vui lòng thử lại.', isStreaming: false } : m
        ))
      }
    } finally {
      setIsStreaming(false)
      abortRef.current = null
    }
  }, [messages, sessionId, model, consumeStream])

  // Reconnect to an in-progress agent run for the given session, if any.
  // Server replies `event: no_active` and closes when nothing is live — we
  // detect that on the first event and bail without disturbing UI state.
  const resumeStream = useCallback(async (id: string) => {
    const abort = new AbortController()
    abortRef.current = abort
    const aiIdRef = { current: '' }

    try {
      const res = await fetch(`${API_URL}/api/chat/sessions/${id}/stream`, { signal: abort.signal })
      if (!res.ok || !res.body) return

      await consumeStream(res, aiIdRef, (firstEventType) => {
        if (firstEventType === 'no_active') return false
        // Live run found — attach to the last assistant message (or create a
        // placeholder if none exists yet) so streamed events append onto it.
        // aiIdRef must be resolved synchronously here because consumeStream
        // dispatches the first event to applyEvent immediately after this call.
        const current = messagesRef.current
        let lastAssistantIdx = -1
        for (let i = current.length - 1; i >= 0; i--) {
          if (current[i].role === 'assistant') { lastAssistantIdx = i; break }
        }
        if (lastAssistantIdx === -1) {
          aiIdRef.current = crypto.randomUUID()
          const newAiId = aiIdRef.current
          setMessages(prev => [...prev, {
            id: newAiId, role: 'assistant', content: '', timestamp: new Date(), steps: [], isStreaming: true,
          }])
        } else {
          aiIdRef.current = current[lastAssistantIdx].id
          setMessages(prev => prev.map((m, i) => i === lastAssistantIdx ? { ...m, isStreaming: true } : m))
        }
        setIsStreaming(true)
        return true
      })
    } catch {
      /* ignore */
    } finally {
      setIsStreaming(false)
      abortRef.current = null
    }
  }, [consumeStream])

  const loadSession = useCallback(async (id: string) => {
    setSessionId(id)
    try {
      const res = await fetch(`${API_URL}/api/chat/sessions/${id}`)
      if (!res.ok) return
      const data = await res.json()
      setMessages(rowsToChatMessages(data.messages as PersistedMessage[]))
      // Try to resume any in-progress agent run for this session — if the
      // server has nothing live, this is a no-op.
      void resumeStream(id)
    } catch { /* ignore */ }
  }, [resumeStream])

  const newSession = useCallback(() => {
    abortRef.current?.abort()
    setMessages([])
    setSessionId(null)
    setIsStreaming(false)
  }, [])

  return { messages, isStreaming, sessionId, sendMessage, newSession, loadSession }
}

export function useSessions(currentSessionId: string | null) {
  const [sessions, setSessions] = useState<ChatSession[]>([])
  const [loading, setLoading] = useState(false)

  const fetchSessions = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetch(`${API_URL}/api/chat/sessions`)
      if (res.ok) setSessions(await res.json())
    } catch { /* ignore */ } finally {
      setLoading(false)
    }
  }, [])

  const deleteSession = useCallback(async (id: string) => {
    try {
      await fetch(`${API_URL}/api/chat/sessions/${id}`, { method: 'DELETE' })
      setSessions(prev => prev.filter(s => s.id !== id))
    } catch { /* ignore */ }
  }, [])

  useEffect(() => { fetchSessions() }, [fetchSessions, currentSessionId])

  return { sessions, loading, fetchSessions, deleteSession }
}

export function useModel() {
  const [models, setModels] = useState<ModelOption[]>([])
  const [selectedModel, setSelectedModel] = useState<string | null>(null)

  useEffect(() => {
    fetch(`${API_URL}/api/chat/models`)
      .then(r => r.json())
      .then(data => { setModels(data.models ?? []); setSelectedModel(data.default ?? null) })
      .catch(() => {})
  }, [])

  const selectModel = useCallback((modelId: string) => {
    setSelectedModel(modelId)
    fetch(`${API_URL}/api/chat/models/preferred`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model: modelId }),
    }).catch(() => {})
  }, [])

  return { models, selectedModel, selectModel }
}
