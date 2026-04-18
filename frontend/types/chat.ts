export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  toolCalls?: ToolCallInfo[]
  isStreaming?: boolean
}

export interface ToolCallInfo {
  name: string
  status: 'running' | 'done'
  result?: string
}

export interface ChatSession {
  id: string
  title: string
  createdAt: string
  updatedAt: string
  messageCount: number
  lastMessage: string | null
}
