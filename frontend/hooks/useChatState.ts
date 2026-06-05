'use client'

import { useState, useCallback, useRef, useEffect } from 'react'
import { API_URL, apiDelete, apiGet, apiJson } from '@/lib/api'
import { applyChatStreamEvent, consumeChatStream } from '@/lib/chatStream'
import { rowsToChatMessages, type PersistedMessage } from '@/lib/chatTimeline'
import type { ChatMessage as ChatMessageType, ChatSession, ModelOption } from '@/types/chat'

type SessionDetail = {
  messages: PersistedMessage[]
}

type ModelsResponse = {
  models?: ModelOption[]
  default?: string | null
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

  const applyEvent = useCallback((eventType: string, data: Record<string, unknown>, aiId: string) => {
    applyChatStreamEvent(setMessages, setSessionId, eventType, data, aiId)
  }, [])

  const consumeStream = useCallback(async (
    res: Response,
    aiIdRef: { current: string },
    onFirstEvent?: (eventType: string, data: Record<string, unknown>) => boolean,
  ) => {
    await consumeChatStream(res, aiIdRef, applyEvent, onFirstEvent)
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
          m.id === aiId ? { ...m, content: m.content || 'Sorry, something went wrong. Please try again.', isStreaming: false } : m
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
      const data = await apiGet<SessionDetail>(`/api/chat/sessions/${id}`)
      setMessages(rowsToChatMessages(data.messages))
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
      setSessions(await apiGet<ChatSession[]>('/api/chat/sessions'))
    } catch { /* ignore */ } finally {
      setLoading(false)
    }
  }, [])

  const deleteSession = useCallback(async (id: string) => {
    try {
      await apiDelete(`/api/chat/sessions/${id}`)
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
    apiGet<ModelsResponse>('/api/chat/models')
      .then(data => { setModels(data.models ?? []); setSelectedModel(data.default ?? null) })
      .catch(() => {})
  }, [])

  const selectModel = useCallback((modelId: string) => {
    setSelectedModel(modelId)
    apiJson('/api/chat/models/preferred', {
      method: 'PUT',
      body: { model: modelId },
    }).catch(() => {})
  }, [])

  return { models, selectedModel, selectModel }
}
