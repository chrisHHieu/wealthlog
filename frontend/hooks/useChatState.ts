'use client'

import { useState, useCallback, useRef, useEffect } from 'react'
import { API_URL, apiDelete, apiGet, apiJson } from '@/lib/api'
import { applyChatStreamEvent, consumeChatStream } from '@/lib/chatStream'
import { rowsToChatMessages, type PersistedMessage } from '@/lib/chatTimeline'
import type { ActionPreview, ActionStatus, ChatMessage as ChatMessageType, ChatSession, ModelOption } from '@/types/chat'

type SessionDetail = {
  messages: PersistedMessage[]
}

type SessionAction = { id: string; status: ActionStatus; preview?: ActionPreview }

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

  /** Mark a streaming assistant message as settled (after abort or error). */
  const finalizeMessage = useCallback((aiId: string, error?: boolean) => {
    setMessages(prev => prev.map(m =>
      m.id === aiId
        ? {
            ...m,
            isStreaming: false,
            error,
            content: error ? (m.content || 'Sorry, something went wrong. Please try again.') : m.content,
            steps: (m.steps || []).map(step =>
              'streaming' in step && step.streaming ? { ...step, streaming: false } : step
            ),
          }
        : m
    ))
  }, [])

  const sendMessage = useCallback(async (content: string, baseMessages?: ChatMessageType[]) => {
    const base = baseMessages ?? messagesRef.current
    const userMsg: ChatMessageType = { id: crypto.randomUUID(), role: 'user', content, timestamp: new Date() }
    const aiId = crypto.randomUUID()

    setMessages([...base, userMsg, {
      id: aiId, role: 'assistant', content: '', timestamp: new Date(), steps: [], isStreaming: true,
    }])
    setIsStreaming(true)

    const history = [...base, userMsg].map(m => ({ role: m.role, content: m.content }))
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
      finalizeMessage(aiId, (err as Error).name !== 'AbortError')
    } finally {
      setIsStreaming(false)
      abortRef.current = null
    }
  }, [sessionId, model, consumeStream, finalizeMessage])

  /** Abort the in-flight run; the catch path in sendMessage settles the message. */
  const stopStreaming = useCallback(() => {
    abortRef.current?.abort()
  }, [])

  /** Re-send the most recent user message, dropping it and the failed reply. */
  const retryLast = useCallback(() => {
    const current = messagesRef.current
    let lastUserIdx = -1
    for (let i = current.length - 1; i >= 0; i--) {
      if (current[i].role === 'user') { lastUserIdx = i; break }
    }
    if (lastUserIdx === -1) return
    void sendMessage(current[lastUserIdx].content, current.slice(0, lastUserIdx))
  }, [sendMessage])

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
      // Settle the attached message in case the stream was aborted mid-run
      if (aiIdRef.current) finalizeMessage(aiIdRef.current)
      setIsStreaming(false)
      abortRef.current = null
    }
  }, [consumeStream, finalizeMessage])

  const loadSession = useCallback(async (id: string) => {
    setSessionId(id)
    try {
      const data = await apiGet<SessionDetail>(`/api/chat/sessions/${id}`)
      // Pull the current status of any deferred writes so reloaded confirm
      // cards show executed/rejected instead of re-prompting.
      const actions = await apiGet<SessionAction[]>(`/api/chat/sessions/${id}/actions`)
        .catch(() => [] as SessionAction[])
      const statusById = Object.fromEntries(actions.map(a => [a.id, a.status]))
      const previewById = Object.fromEntries(
        actions.filter(a => a.preview).map(a => [a.id, a.preview as ActionPreview]),
      )
      setMessages(rowsToChatMessages(data.messages, statusById, previewById))
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

  return { messages, isStreaming, sessionId, sendMessage, stopStreaming, retryLast, newSession, loadSession }
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
