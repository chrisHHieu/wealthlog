'use client'

import { motion, AnimatePresence } from 'framer-motion'
import {
  ChevronDown, ChevronRight, Check, Copy, Brain, Wrench,
  MessageSquare, AlertCircle, RotateCcw, Sparkles,
} from 'lucide-react'
import { memo, useEffect, useRef, useState } from 'react'
import Image from 'next/image'
import { cn } from '@/lib/utils'
import { MarkdownMessage } from '@/components/chat/MarkdownMessage'
import { useSmoothText } from '@/hooks/useSmoothText'
import type { ChatMessage as ChatMessageType, ChatStep } from '@/types/chat'

const TOOL_LABELS: Record<string, string> = {
  // Reports
  get_financial_summary:        'View financial overview',
  get_spending_trends:          'Analyze spending trends',
  get_top_expenses:             'View top expenses',
  get_upcoming_bills:           'Check upcoming bills',
  get_monthly_digest:           'Read monthly digest',
  // Transactions
  search_transactions:          'Search transactions',
  get_spending_by_category:     'View spending by category',
  get_income_by_category:       'View income by category',
  create_transaction:           'Create transaction',
  create_multiple_transactions: 'Create multiple transactions',
  update_transaction:           'Update transactions',
  delete_transaction:           'Delete transactions',
  // Accounts
  get_accounts:                 'View accounts',
  get_account_summary:          'View account overview',
  // Budgets
  get_budget_status:            'Check budget',
  // Goals
  get_goals:                    'View savings goals',
  // Investments
  get_portfolio:                'View investment portfolio',
  // Memory
  list_my_facts:                'View remembered facts',
  forget_fact:                  'Delete remembered fact',
  edit_fact:                    'Update remembered fact',
  verify_fact:                  'Confirm remembered fact',
  list_commitments:             'View commitments',
  complete_commitment:          'Mark commitment complete',
  dismiss_commitment:           'Dismiss commitment',
  // Analytics
  query_database:               'Analyze data',
}

function formatSeconds(ms: number): string {
  const s = ms / 1000
  return s >= 10 ? `${Math.round(s)}s` : `${s.toFixed(1)}s`
}

/**
 * Renders streamed text as a stable prefix plus a freshly-faded tail chunk —
 * each delta remounts the tail span so new characters fade in softly.
 */
function FadingText({ text }: { text: string }) {
  const prevLenRef = useRef(0)
  const stableLen = Math.min(prevLenRef.current, text.length)
  const stable = text.slice(0, stableLen)
  const tail = text.slice(stableLen)

  useEffect(() => {
    prevLenRef.current = text.length
  }, [text])

  return (
    <>
      {stable}
      {tail && <span key={text.length} className="chat-fade-chunk">{tail}</span>}
    </>
  )
}

/**
 * One-line live ticker for the current thought. Left-aligned while the line
 * fits; once it overflows, it stays scrolled to the tail with the left edge
 * fading out.
 */
function ThinkingTicker({ text }: { text: string }) {
  const ref = useRef<HTMLDivElement>(null)
  const [overflowing, setOverflowing] = useState(false)

  useEffect(() => {
    const el = ref.current
    if (!el) return
    el.scrollLeft = el.scrollWidth
    const isOverflowing = el.scrollWidth > el.clientWidth + 1
    if (isOverflowing !== overflowing) setOverflowing(isOverflowing)
  }, [text, overflowing])

  return (
    <div ref={ref} className={cn('chat-thinking-preview', overflowing && 'chat-thinking-preview--masked')}>
      <FadingText text={text} />
    </div>
  )
}

interface Props {
  message: ChatMessageType
  onRetry?: () => void
}

export const ChatMessage = memo(function ChatMessage({ message, onRetry }: Props) {
  const isUser = message.role === 'user'

  if (isUser) {
    return (
      <motion.div
        className="chat-msg chat-msg-user"
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
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
  // Plain content without steps: error replies and legacy persisted messages
  const fallbackContent = steps.length === 0 && !message.isStreaming ? message.content : null

  // Show pending dots only before ANY event has arrived (no content, no steps).
  const showPendingDots = message.isStreaming && steps.length === 0 && !message.content

  return (
    <motion.div
      className="chat-msg chat-msg-ai"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
    >
      <div className={cn('chat-ai-icon', message.isStreaming && 'streaming')}>
        <Image src="/images/ai-avatar.png" alt="Expensep" width={32} height={32} />
      </div>

      <div className="chat-ai-body">
        {showPendingDots && (
          <div className="chat-inline-dots" aria-label="Processing">
            <span /><span /><span />
          </div>
        )}

        {/* Work trail: live timeline while streaming, one collapsed row when done */}
        {intermediateSteps.length > 0 && (
          message.isStreaming
            ? <ReactTimeline steps={intermediateSteps} live />
            : <TrailSummary steps={intermediateSteps} durationMs={message.workDurationMs} />
        )}

        {/* Final answer — smooth-revealed, block-memoized markdown */}
        {finalAnswer && finalAnswer.kind === 'text' && (
          <FinalAnswer step={finalAnswer} />
        )}

        {fallbackContent && (
          <div className="chat-md">
            <MarkdownMessage content={fallbackContent} />
          </div>
        )}

        {!message.isStreaming && (finalAnswer?.content || fallbackContent) && (
          <MessageActions
            content={finalAnswer?.content || fallbackContent || ''}
            error={message.error}
            onRetry={onRetry}
          />
        )}
      </div>
    </motion.div>
  )
})

/** Final assistant answer: smooth character reveal + memoized markdown blocks. */
function FinalAnswer({ step }: { step: Extract<ChatStep, { kind: 'text' }> }) {
  const smooth = useSmoothText(step.content, !!step.streaming)

  return (
    <div className={cn('chat-md', step.streaming && 'chat-md--live')}>
      {smooth ? (
        <MarkdownMessage content={smooth} />
      ) : (
        <div className="chat-inline-dots" aria-label="Processing">
          <span /><span /><span />
        </div>
      )}
    </div>
  )
}

function MessageActions({ content, error, onRetry }: { content: string; error?: boolean; onRetry?: () => void }) {
  const [copied, setCopied] = useState(false)

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(content)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch { /* clipboard unavailable */ }
  }

  return (
    <div className="chat-msg-actions">
      <button className="chat-msg-action-btn" onClick={copy} title="Copy answer">
        {copied ? <Check size={12} /> : <Copy size={12} />}
        <span>{copied ? 'Copied' : 'Copy'}</span>
      </button>
      {error && onRetry && (
        <button className="chat-msg-action-btn chat-msg-action-btn--retry" onClick={onRetry} title="Retry">
          <RotateCcw size={12} />
          <span>Retry</span>
        </button>
      )}
    </div>
  )
}

/** Collapsed one-line summary of the agent's work, expandable to the full timeline. */
function TrailSummary({ steps, durationMs }: { steps: ChatStep[]; durationMs?: number }) {
  const [expanded, setExpanded] = useState(false)
  const stepLabel = `${steps.length} step${steps.length > 1 ? 's' : ''}`

  return (
    <div className="chat-trail">
      <button className="chat-trail-toggle" onClick={() => setExpanded(!expanded)}>
        {expanded ? <ChevronDown size={11} /> : <ChevronRight size={11} />}
        <Sparkles size={11} />
        <span>
          {durationMs ? `Worked for ${formatSeconds(durationMs)}` : 'Worked'} · {stepLabel}
        </span>
      </button>
      <AnimatePresence initial={false}>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            style={{ overflow: 'hidden' }}
          >
            <ReactTimeline steps={steps} live={false} />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

function ReactTimeline({ steps, live }: { steps: ChatStep[]; live: boolean }) {
  return (
    <div className="chat-timeline">
      {steps.map((step, i) => (
        <TimelineStep key={`${step.kind}-${step.stepId}-${i}`} step={step} live={live} />
      ))}
    </div>
  )
}

function ThinkingStep({ step }: { step: Extract<ChatStep, { kind: 'thinking' }> }) {
  const [expanded, setExpanded] = useState(false)
  const hasContent = !!step.content
  // Single-line live ticker: the latest line of thought, tail-end only
  const lines = step.content.split('\n')
  let lastLine = ''
  for (let i = lines.length - 1; i >= 0; i--) {
    if (lines[i].trim()) { lastLine = lines[i].trim(); break }
  }
  const preview = lastLine.slice(-140)

  return (
    <div className="chat-step chat-step-thinking">
      <div className="chat-step-connector">
        <div className="chat-step-dot chat-step-dot-thinking">
          {step.streaming ? (
            <span className="chat-spinner-ring" />
          ) : (
            <Brain size={12} />
          )}
        </div>
      </div>
      <div className="chat-step-body">
        <button
          className="chat-step-header"
          onClick={() => hasContent && setExpanded(!expanded)}
          disabled={!hasContent}
        >
          {hasContent && (expanded ? <ChevronDown size={11} /> : <ChevronRight size={11} />)}
          <span className={cn('chat-step-label', step.streaming && 'chat-shimmer-text')}>
            {step.streaming
              ? 'Thinking…'
              : step.durationMs
                ? `Thought for ${formatSeconds(step.durationMs)}`
                : 'Deep thinking'}
          </span>
        </button>

        {/* Streaming + collapsed: soft live preview of the current thought */}
        {step.streaming && !expanded && hasContent && (
          <ThinkingTicker text={preview} />
        )}

        <AnimatePresence initial={false}>
          {expanded && hasContent && (
            <motion.div
              className="chat-step-content chat-step-thinking-content"
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.15 }}
            >
              <pre className="chat-step-thinking-text">
                {step.streaming ? <FadingText text={step.content} /> : step.content}
              </pre>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}

function TimelineStep({ step, live }: { step: ChatStep; live: boolean }) {
  const [expanded, setExpanded] = useState(false)

  if (step.kind === 'thinking') {
    return <ThinkingStep step={step} />
  }

  if (step.kind === 'text') {
    // Intermediate text = thought (reasoning before a tool call)
    return (
      <div className="chat-step chat-step-thought">
        <div className="chat-step-connector">
          <div className="chat-step-dot chat-step-dot-thought">
            <MessageSquare size={12} />
          </div>
        </div>
        <div className="chat-step-body">
          <div className="chat-step-label chat-step-label-inline">Reasoning</div>
          <div className="chat-step-thought-text">
            {step.streaming ? <FadingText text={step.content} /> : step.content}
          </div>
        </div>
      </div>
    )
  }

  // Tool step
  const hasInput = !!step.input && Object.keys(step.input).length > 0
  const hasResult = step.status === 'done' && !!step.result
  const canExpand = hasInput || hasResult
  const label = TOOL_LABELS[step.name] ?? step.name
  const isError = step.status === 'error'
  const isRunning = step.status === 'running'

  return (
    <div className={cn('chat-step chat-step-tool', isRunning && 'chat-step--running')}>
      <div className="chat-step-connector">
        <div className={cn(
          'chat-step-dot',
          isRunning ? 'chat-step-dot-running'
            : isError ? 'chat-step-dot-error'
            : 'chat-step-dot-done',
          live && step.status === 'done' && 'chat-step-dot-burst',
        )}>
          {isRunning ? (
            <span className="chat-spinner-ring" />
          ) : isError ? (
            <AlertCircle size={12} />
          ) : (
            <Check size={12} strokeWidth={2.5} />
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
          <span className={cn('chat-step-label', isRunning && 'chat-shimmer-text')}>{label}</span>
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
              {hasInput && (
                <>
                  <div className="chat-step-observation-label">
                    <span>Parameters</span>
                  </div>
                  <div className="chat-step-input-params">
                    {Object.entries(step.input!).map(([k, v]) => (
                      <div key={k} className="chat-step-param-row">
                        <span className="chat-step-param-key">{k}</span>
                        <span className="chat-step-param-val">
                          {typeof v === 'object' ? JSON.stringify(v) : String(v)}
                        </span>
                      </div>
                    ))}
                  </div>
                </>
              )}
              {hasResult && (
                <>
                  <div className="chat-step-observation-label" style={{ marginTop: hasInput ? 'var(--space-3)' : 0 }}>
                    <span>Result</span>
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
