import type { ActionPreview, ActionStatus, ChatMessage, ChatStep } from '@/types/chat'

const ACTION_ID_RE = /action_id=([0-9a-fA-F-]{36})/

export type PersistedBlock = {
  type?: string
  text?: string
  thinking?: string
  id?: string
  name?: string
  input?: Record<string, unknown>
  tool_use_id?: string
  content?: unknown
}

export type PersistedMessage = {
  id: string
  role: 'user' | 'assistant'
  content: string
  blocks?: PersistedBlock[] | null
  createdAt: string
}

function isToolResultOnlyRow(message: PersistedMessage): boolean {
  return (
    !!message.blocks &&
    message.blocks.length > 0 &&
    message.blocks.every(block => block?.type === 'tool_result')
  )
}

function toolResultText(content: unknown): string {
  if (typeof content === 'string') return content
  try {
    return JSON.stringify(content)
  } catch {
    return String(content)
  }
}

export function rowsToChatMessages(
  rows: PersistedMessage[],
  actionStatusById: Record<string, ActionStatus> = {},
  actionPreviewById: Record<string, ActionPreview> = {},
): ChatMessage[] {
  const resultByToolUseId = new Map<string, string>()
  for (const message of rows) {
    if (!message.blocks) continue
    for (const block of message.blocks) {
      if (block?.type === 'tool_result' && typeof block.tool_use_id === 'string') {
        resultByToolUseId.set(block.tool_use_id, toolResultText(block.content))
      }
    }
  }

  const output: ChatMessage[] = []
  let currentAssistant: ChatMessage | null = null

  for (const message of rows) {
    if (message.role === 'user' && !isToolResultOnlyRow(message)) {
      output.push({
        id: message.id,
        role: 'user',
        content: message.content,
        timestamp: new Date(message.createdAt),
      })
      currentAssistant = null
      continue
    }

    if (message.role === 'assistant') {
      if (!currentAssistant) {
        currentAssistant = {
          id: message.id,
          role: 'assistant',
          content: '',
          timestamp: new Date(message.createdAt),
          steps: [],
        }
        output.push(currentAssistant)
      }

      const blocks = message.blocks || []
      if (blocks.length === 0 && message.content) {
        currentAssistant.steps!.push({
          kind: 'text',
          stepId: message.id,
          content: message.content,
        })
        currentAssistant.content += message.content
        continue
      }

      blocks.forEach((block, index) => {
        const stepId = `${message.id}-${index}`
        if (block?.type === 'thinking') {
          currentAssistant!.steps!.push({
            kind: 'thinking',
            stepId,
            content: block.thinking || '',
          })
        } else if (block?.type === 'text' && block.text) {
          currentAssistant!.steps!.push({ kind: 'text', stepId, content: block.text })
          currentAssistant!.content += block.text
        } else if (block?.type === 'tool_use' && typeof block.id === 'string') {
          const result = resultByToolUseId.get(block.id)
          const step: ChatStep = {
            kind: 'tool',
            stepId,
            id: block.id,
            name: block.name || '',
            input: block.input,
            result,
            status: 'done',
          }
          // Recover a deferred write from its tool_result text (it embeds
          // action_id=…). Its live status comes from the actions endpoint.
          const actionId = result ? ACTION_ID_RE.exec(result)?.[1] : undefined
          if (actionId) {
            step.pendingActionId = actionId
            step.actionStatus = actionStatusById[actionId] ?? 'pending'
            step.preview = actionPreviewById[actionId]
          }
          currentAssistant!.steps!.push(step)
        }
      })
    }
  }

  return output
}
