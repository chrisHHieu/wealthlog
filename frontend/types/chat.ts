export type ChatStep =
  | {
      kind: 'thinking'
      stepId: string
      content: string
      streaming?: boolean
      startedAt?: number
      durationMs?: number
    }
  | {
      kind: 'text'
      stepId: string
      content: string
      streaming?: boolean
      final?: boolean  // true = this was the final answer
    }
  | {
      kind: 'tool'
      stepId: string
      id: string
      name: string
      input?: Record<string, unknown>
      result?: string
      status: 'running' | 'done' | 'error'
      /** Set when this was a write deferred for confirmation (see ActionStatus). */
      pendingActionId?: string
      actionStatus?: ActionStatus
      /** Human-readable effect of the deferred write, shown on the confirm card. */
      preview?: ActionPreview
    }

/** Lifecycle of a deferred financial write awaiting user confirmation. */
export type ActionStatus = 'pending' | 'executed' | 'rejected' | 'failed'

/** Render-ready summary of what a deferred write will do (resolves UUIDs, shows diffs). */
export interface ActionPreview {
  summary: string
  items: { label: string; detail?: string }[]
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  steps?: ChatStep[]
  isStreaming?: boolean
  /** Total wall-clock time of the agent run, set when the stream completes. */
  workDurationMs?: number
  /** Set when the request failed; enables the retry action. */
  error?: boolean
}

export interface ModelOption {
  id: string
  name: string
  description: string
}

export interface ChatSession {
  id: string
  title: string
  createdAt: string
  updatedAt: string
  messageCount: number
  lastMessage: string | null
}
