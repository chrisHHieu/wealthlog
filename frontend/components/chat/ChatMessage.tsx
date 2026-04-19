'use client'

import { motion, AnimatePresence } from 'framer-motion'
import { Sparkles, ChevronDown, ChevronRight, Check, Loader2, Brain, Wrench, Eye, MessageSquare } from 'lucide-react'
import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { cn } from '@/lib/utils'
import type { ChatMessage as ChatMessageType, ChatStep } from '@/types/chat'

interface Props {
  message: ChatMessageType
}

export function ChatMessage({ message }: Props) {
  const isUser = message.role === 'user'

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

  const steps = message.steps || []
  // The LAST step being text = final answer (rendered as markdown, even while streaming).
  // If a later tool call appears, this same text step gets reclassified as intermediate reasoning.
  const lastStep = steps[steps.length - 1]
  const finalIsText = lastStep?.kind === 'text'
  const intermediateSteps = finalIsText ? steps.slice(0, -1) : steps
  const finalAnswer = finalIsText ? lastStep : null

  // Show pending dots only before ANY event has arrived (no content, no steps).
  const showPendingDots = message.isStreaming && steps.length === 0 && !message.content

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
        {showPendingDots && (
          <div className="chat-inline-dots" aria-label="Đang xử lý">
            <span /><span /><span />
          </div>
        )}

        {/* Timeline of intermediate steps (thinking → thoughts → actions → observations) */}
        {intermediateSteps.length > 0 && (
          <ReactTimeline steps={intermediateSteps} />
        )}

        {/* Final answer — rendered as full markdown (incrementally during streaming) */}
        {finalAnswer && finalAnswer.kind === 'text' && (
          <div className={cn('chat-md', finalAnswer.streaming && 'streaming')}>
            {finalAnswer.content ? (
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{finalAnswer.content}</ReactMarkdown>
            ) : (
              <div className="chat-inline-dots" aria-label="Đang xử lý">
                <span /><span /><span />
              </div>
            )}
            {finalAnswer.streaming && finalAnswer.content && <span className="chat-cursor" />}
          </div>
        )}
      </div>
    </motion.div>
  )
}

function ReactTimeline({ steps }: { steps: ChatStep[] }) {
  return (
    <div className="chat-timeline">
      {steps.map((step, i) => (
        <TimelineStep key={`${step.kind}-${step.stepId}-${i}`} step={step} />
      ))}
    </div>
  )
}

function TimelineStep({ step }: { step: ChatStep }) {
  const [expanded, setExpanded] = useState(false)

  if (step.kind === 'thinking') {
    return (
      <div className="chat-step chat-step-thinking">
        <div className="chat-step-connector">
          <div className="chat-step-dot chat-step-dot-thinking">
            {step.streaming ? (
              <Loader2 size={11} className="chat-step-spin" />
            ) : (
              <Brain size={11} />
            )}
          </div>
        </div>
        <div className="chat-step-body">
          <button className="chat-step-header" onClick={() => setExpanded(!expanded)}>
            {expanded ? <ChevronDown size={11} /> : <ChevronRight size={11} />}
            <span className="chat-step-label">
              {step.streaming ? 'Đang suy nghĩ...' : 'Suy nghĩ sâu'}
            </span>
          </button>
          <AnimatePresence initial={false}>
            {expanded && (
              <motion.div
                className="chat-step-content chat-step-thinking-content"
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.2 }}
              >
                <div className="chat-step-text">{step.content}</div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    )
  }

  if (step.kind === 'text') {
    // Intermediate text = thought (reasoning before a tool call)
    return (
      <div className="chat-step chat-step-thought">
        <div className="chat-step-connector">
          <div className="chat-step-dot chat-step-dot-thought">
            <MessageSquare size={11} />
          </div>
        </div>
        <div className="chat-step-body">
          <div className="chat-step-label chat-step-label-inline">Lập luận</div>
          <div className="chat-step-thought-text">
            {step.content}
            {step.streaming && <span className="chat-cursor" />}
          </div>
        </div>
      </div>
    )
  }

  // Tool step
  const hasResult = step.status === 'done' && !!step.result
  const hasInput = !!step.input && Object.keys(step.input).length > 0
  const canExpand = hasResult || hasInput
  const inputPreview = step.input ? formatToolInputPreview(step.input) : null
  const fullInput = step.input ? formatToolInputFull(step.input) : null

  return (
    <div className="chat-step chat-step-tool">
      <div className="chat-step-connector">
        <div className={cn(
          'chat-step-dot',
          step.status === 'running' ? 'chat-step-dot-running' : 'chat-step-dot-done',
        )}>
          {step.status === 'running' ? (
            <Loader2 size={11} className="chat-step-spin" />
          ) : (
            <Check size={11} />
          )}
        </div>
      </div>
      <div className="chat-step-body">
        <button
          className="chat-step-header"
          onClick={() => canExpand && setExpanded(!expanded)}
          disabled={!canExpand}
        >
          {canExpand && (expanded ? <ChevronDown size={11} /> : <ChevronRight size={11} />)}
          <Wrench size={11} className="chat-step-icon" />
          <span className="chat-step-label">{step.name}</span>
          {inputPreview && (
            <code className="chat-step-input">{inputPreview}</code>
          )}
        </button>
        <AnimatePresence initial={false}>
          {expanded && canExpand && (
            <motion.div
              className="chat-step-content chat-step-observation"
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.2 }}
            >
              {fullInput && (
                <>
                  <div className="chat-step-observation-label">
                    <Wrench size={10} />
                    <span>Tham số</span>
                  </div>
                  <pre className="chat-step-result">{fullInput}</pre>
                </>
              )}
              {hasResult && (
                <>
                  <div className="chat-step-observation-label">
                    <Eye size={10} />
                    <span>Kết quả</span>
                  </div>
                  <pre className="chat-step-result">{step.result}</pre>
                </>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}

/** One-line header preview: short, fits on the step header next to the tool name. */
function formatToolInputPreview(input: Record<string, unknown>): string {
  const keys = Object.keys(input)
  if (keys.length === 0) return '()'
  const short = keys
    .map(k => {
      const v = input[k]
      const strVal = typeof v === 'string' ? `"${v}"` : JSON.stringify(v)
      return `${k}: ${strVal.length > 20 ? strVal.slice(0, 20) + '…' : strVal}`
    })
    .join(', ')
  return short.length > 50 ? short.slice(0, 50) + '…' : short
}

/** Full pretty-printed input for the expanded view — shown verbatim, no truncation. */
function formatToolInputFull(input: Record<string, unknown>): string {
  try {
    return JSON.stringify(input, null, 2)
  } catch {
    return String(input)
  }
}
