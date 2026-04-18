'use client'

import { motion } from 'framer-motion'
import { Sparkles, ChevronDown, ChevronRight, Check, Loader2 } from 'lucide-react'
import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { cn } from '@/lib/utils'
import type { ChatMessage as ChatMessageType } from '@/types/chat'

interface Props {
  message: ChatMessageType
}

export function ChatMessage({ message }: Props) {
  const isUser = message.role === 'user'
  const [toolsExpanded, setToolsExpanded] = useState(false)

  if (isUser) {
    return (
      <motion.div
        className="chat-msg chat-msg-user"
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.2 }}
      >
        <div className="chat-user-bubble">{message.content}</div>
      </motion.div>
    )
  }

  return (
    <motion.div
      className="chat-msg chat-msg-ai"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
    >
      <div className="chat-ai-icon">
        <Sparkles size={14} />
      </div>

      <div className="chat-ai-body">
        {/* Tool calls */}
        {message.toolCalls && message.toolCalls.length > 0 && (
          <button
            className="chat-tools-toggle"
            onClick={() => setToolsExpanded(!toolsExpanded)}
          >
            {toolsExpanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
            <span>
              {message.toolCalls.filter(t => t.status === 'running').length > 0
                ? `Đang phân tích...`
                : `Đã dùng ${message.toolCalls.length} công cụ`
              }
            </span>
          </button>
        )}

        {toolsExpanded && message.toolCalls && (
          <motion.div
            className="chat-tools-list"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            transition={{ duration: 0.2 }}
          >
            {message.toolCalls.map((tool, i) => (
              <div key={i} className="chat-tool-item">
                {tool.status === 'running' ? (
                  <Loader2 size={11} className="chat-tool-spinner" />
                ) : (
                  <Check size={11} className="chat-tool-done" />
                )}
                <span>{tool.name}</span>
              </div>
            ))}
          </motion.div>
        )}

        {/* Markdown content */}
        {message.content && (
          <div className={cn('chat-md', message.isStreaming && 'streaming')}>
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
            {message.isStreaming && <span className="chat-cursor" />}
          </div>
        )}
      </div>
    </motion.div>
  )
}
