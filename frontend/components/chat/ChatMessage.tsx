'use client'

import { motion, AnimatePresence } from 'framer-motion'
import { ChevronDown, ChevronRight, Check, Loader2, Brain, Wrench, Eye, MessageSquare, AlertCircle } from 'lucide-react'
import { useState, useEffect, useRef } from 'react'
import Image from 'next/image'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { cn } from '@/lib/utils'
import type { ChatMessage as ChatMessageType, ChatStep } from '@/types/chat'

const TOOL_LABELS: Record<string, string> = {
  // Reports
  get_financial_summary:        'Xem tổng quan tài chính',
  get_spending_trends:          'Phân tích xu hướng chi tiêu',
  get_top_expenses:             'Xem chi tiêu lớn nhất',
  get_upcoming_bills:           'Kiểm tra hóa đơn sắp tới',
  get_monthly_digest:           'Đọc báo cáo tháng',
  // Transactions
  search_transactions:          'Tìm kiếm giao dịch',
  get_spending_by_category:     'Xem chi tiêu theo danh mục',
  get_income_by_category:       'Xem thu nhập theo danh mục',
  create_transaction:           'Tạo giao dịch',
  create_multiple_transactions: 'Tạo nhiều giao dịch',
  update_transaction:           'Cập nhật giao dịch',
  delete_transaction:           'Xóa giao dịch',
  // Accounts
  get_accounts:                 'Xem danh sách tài khoản',
  get_account_summary:          'Xem tổng quan tài khoản',
  // Budgets
  get_budget_status:            'Kiểm tra ngân sách',
  // Goals
  get_goals:                    'Xem mục tiêu tiết kiệm',
  // Investments
  get_portfolio:                'Xem danh mục đầu tư',
  // Memory
  list_my_facts:                'Xem thông tin đã ghi nhớ',
  forget_fact:                  'Xóa thông tin đã ghi nhớ',
  edit_fact:                    'Cập nhật thông tin đã ghi nhớ',
  verify_fact:                  'Xác nhận thông tin đã ghi nhớ',
  list_commitments:             'Xem cam kết',
  complete_commitment:          'Đánh dấu cam kết hoàn thành',
  dismiss_commitment:           'Bỏ qua cam kết',
  // Analytics
  query_database:               'Phân tích dữ liệu',
}

interface Props {
  message: ChatMessageType
}

export function ChatMessage({ message }: Props) {
  const isUser = message.role === 'user'

  if (isUser) {
    return (
      <motion.div
        className="chat-msg chat-msg-user"
        initial={{ opacity: 0, y: 15, scale: 0.98 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
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
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
    >
      <div className="chat-ai-icon">
        <Image src="/images/ai-avatar.png" alt="Chip" width={32} height={32} />
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

function ThinkingStep({ step }: { step: Extract<ChatStep, { kind: 'thinking' }> }) {
  const [expanded, setExpanded] = useState(false)
  const thinkingRef = useRef<HTMLPreElement>(null)
  const [isThinkingAutoScroll, setIsThinkingAutoScroll] = useState(true)
  const hasContent = !!step.content
  // Track if this step was ever streaming so we know when it *finishes*
  const wasStreamingRef = useRef(step.streaming)

  useEffect(() => {
    if (step.streaming) {
      wasStreamingRef.current = true
    }
  }, [step.streaming])

  // Auto-expand when streaming finishes so user sees the result immediately
  useEffect(() => {
    if (!step.streaming && wasStreamingRef.current && hasContent) {
      setExpanded(true)
    }
  }, [step.streaming, hasContent])

  const handleThinkingScroll = () => {
    if (!thinkingRef.current) return
    const { scrollTop, scrollHeight, clientHeight } = thinkingRef.current
    const isAtBottom = scrollHeight - scrollTop - clientHeight < 20
    setIsThinkingAutoScroll(isAtBottom)
  }

  // Auto-scroll to bottom while streaming
  useEffect(() => {
    if (step.streaming && thinkingRef.current && isThinkingAutoScroll) {
      thinkingRef.current.scrollTop = thinkingRef.current.scrollHeight
    }
  }, [step.content, step.streaming, isThinkingAutoScroll])

  const showContent = step.streaming ? hasContent : expanded && hasContent

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
        <button
          className="chat-step-header"
          onClick={() => hasContent && !step.streaming && setExpanded(!expanded)}
          disabled={!hasContent || step.streaming}
        >
          {hasContent && !step.streaming && (
            expanded ? <ChevronDown size={11} /> : <ChevronRight size={11} />
          )}
          <span className="chat-step-label">
            {step.streaming ? 'Đang suy nghĩ...' : 'Suy nghĩ sâu'}
          </span>
          {!step.streaming && hasContent && (
            <span className="chat-step-thinking-chars">
              ~{(step.content.length / 4).toFixed(0)} tokens
            </span>
          )}
        </button>
        <AnimatePresence initial={false}>
          {showContent && (
            <motion.div
              className="chat-step-content chat-step-thinking-content"
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.15 }}
            >
              <pre className="chat-step-thinking-text" ref={thinkingRef} onScroll={handleThinkingScroll}>
                {step.content}
                {step.streaming && <span className="chat-cursor" />}
              </pre>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}

function TimelineStep({ step }: { step: ChatStep }) {
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
  const hasInput = !!step.input && Object.keys(step.input).length > 0
  const hasResult = step.status === 'done' && !!step.result
  const canExpand = hasInput || hasResult
  const label = TOOL_LABELS[step.name] ?? step.name
  const isError = step.status === 'error'

  return (
    <div className="chat-step chat-step-tool">
      <div className="chat-step-connector">
        <div className={cn(
          'chat-step-dot',
          step.status === 'running' ? 'chat-step-dot-running'
            : isError ? 'chat-step-dot-error'
            : 'chat-step-dot-done',
        )}>
          {step.status === 'running' ? (
            <Loader2 size={11} className="chat-step-spin" />
          ) : isError ? (
            <AlertCircle size={11} />
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
          <span className="chat-step-label">{label}</span>
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
                  <div className="chat-step-observation-label chat-step-observation-label--input">
                    <Eye size={10} />
                    <span>Tham số</span>
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

