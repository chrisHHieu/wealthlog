import type { Dispatch, SetStateAction } from 'react'
import type { ChatMessage } from '@/types/chat'

type StreamData = Record<string, unknown>
type SetMessages = Dispatch<SetStateAction<ChatMessage[]>>

export function applyChatStreamEvent(
  setMessages: SetMessages,
  setSessionId: (id: string) => void,
  eventType: string,
  data: StreamData,
  aiId: string,
) {
  if (eventType === 'session') {
    setSessionId(data.session_id as string)
  } else if (eventType === 'thinking_start') {
    setMessages(prev => prev.map(message => message.id !== aiId ? message : {
      ...message,
      steps: [
        ...(message.steps || []),
        {
          kind: 'thinking' as const,
          stepId: data.step_id as string,
          content: '',
          streaming: true,
          startedAt: Date.now(),
        },
      ],
    }))
  } else if (eventType === 'thinking_delta') {
    setMessages(prev => prev.map(message => message.id !== aiId ? message : {
      ...message,
      steps: (message.steps || []).map(step =>
        step.kind === 'thinking' && step.stepId === data.step_id
          ? { ...step, content: step.content + (data.text as string) }
          : step
      ),
    }))
  } else if (eventType === 'thinking_stop') {
    setMessages(prev => prev.map(message => message.id !== aiId ? message : {
      ...message,
      steps: (message.steps || []).map(step =>
        step.kind === 'thinking' && step.stepId === data.step_id
          ? { ...step, streaming: false, durationMs: step.startedAt ? Date.now() - step.startedAt : undefined }
          : step
      ),
    }))
  } else if (eventType === 'text_start') {
    setMessages(prev => prev.map(message => message.id !== aiId ? message : {
      ...message,
      steps: [
        ...(message.steps || []),
        { kind: 'text' as const, stepId: data.step_id as string, content: '', streaming: true },
      ],
    }))
  } else if (eventType === 'text_delta') {
    setMessages(prev => prev.map(message => {
      if (message.id !== aiId) return message
      const steps = message.steps || []
      const hasStep = steps.some(step => step.kind === 'text' && step.stepId === data.step_id)
      const nextSteps = hasStep
        ? steps.map(step =>
          step.kind === 'text' && step.stepId === data.step_id
            ? { ...step, content: step.content + (data.text as string) }
            : step
        )
        : [
          ...steps,
          {
            kind: 'text' as const,
            stepId: data.step_id as string,
            content: data.text as string,
            streaming: true,
          },
        ]
      return { ...message, steps: nextSteps, content: message.content + (data.text as string) }
    }))
  } else if (eventType === 'text_stop') {
    setMessages(prev => prev.map(message => message.id !== aiId ? message : {
      ...message,
      steps: (message.steps || []).map(step =>
        step.kind === 'text' && step.stepId === data.step_id
          ? { ...step, streaming: false }
          : step
      ),
    }))
  } else if (eventType === 'tool_start') {
    setMessages(prev => prev.map(message => message.id !== aiId ? message : {
      ...message,
      steps: [
        ...(message.steps || []),
        {
          kind: 'tool' as const,
          stepId: data.step_id as string,
          id: data.id as string,
          name: data.name as string,
          status: 'running' as const,
        },
      ],
    }))
  } else if (eventType === 'tool_input') {
    setMessages(prev => prev.map(message => message.id !== aiId ? message : {
      ...message,
      steps: (message.steps || []).map(step =>
        step.kind === 'tool' && step.id === data.id
          ? { ...step, input: data.input as Record<string, unknown> }
          : step
      ),
    }))
  } else if (eventType === 'tool_done') {
    setMessages(prev => prev.map(message => message.id !== aiId ? message : {
      ...message,
      steps: (message.steps || []).map(step =>
        step.kind === 'tool' && step.id === data.id
          ? {
            ...step,
            status: data.is_error ? 'error' as const : 'done' as const,
            result: data.result as string,
          }
          : step
      ),
    }))
  } else if (eventType === 'done') {
    setMessages(prev => prev.map(message => {
      if (message.id !== aiId) return message
      const steps = message.steps || []
      let lastTextIndex = -1
      for (let index = steps.length - 1; index >= 0; index--) {
        if (steps[index].kind === 'text') {
          lastTextIndex = index
          break
        }
      }
      return {
        ...message,
        steps: steps.map((step, index) =>
          index === lastTextIndex && step.kind === 'text'
            ? { ...step, final: true, streaming: false }
            : step
        ),
        isStreaming: false,
        workDurationMs: Date.now() - message.timestamp.getTime(),
      }
    }))
  }
}

export async function consumeChatStream(
  response: Response,
  aiIdRef: { current: string },
  applyEvent: (eventType: string, data: StreamData, aiId: string) => void,
  onFirstEvent?: (eventType: string, data: StreamData) => boolean,
) {
  if (!response.body) return
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let firstEventSeen = false

  // Batch SSE events per animation frame: fast token streams emit dozens of
  // events per second, and applying each one individually re-renders (and
  // re-parses markdown) far more often than the screen can show.
  const queue: Array<{ type: string; data: StreamData }> = []
  let flushScheduled = false
  const flush = () => {
    flushScheduled = false
    for (const event of queue.splice(0)) {
      applyEvent(event.type, event.data, aiIdRef.current)
    }
  }
  const enqueue = (type: string, data: StreamData) => {
    queue.push({ type, data })
    if (!flushScheduled) {
      flushScheduled = true
      requestAnimationFrame(flush)
    }
  }

  try {
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
          enqueue(eventType, data)
          eventType = ''
        }
      }
    }
  } finally {
    flush()
  }
}
