export type ChatStep =
  | {
      kind: 'thinking'
      stepId: string
      content: string
      streaming?: boolean
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
    }

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  steps?: ChatStep[]
  isStreaming?: boolean
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
