'use client'

import { motion, AnimatePresence } from 'framer-motion'
import { Sparkles, ChevronDown, ChevronRight, Check, Loader2, Brain, Wrench, Eye, MessageSquare, AlertCircle } from 'lucide-react'
import { useState } from 'react'
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
          <div className="chat-step-header">
            <span className="chat-step-label">
              {step.streaming ? 'Đang suy nghĩ...' : 'Suy nghĩ sâu'}
            </span>
          </div>
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
          onClick={() => hasResult && setExpanded(!expanded)}
          disabled={!hasResult}
        >
          {hasResult && (expanded ? <ChevronDown size={11} /> : <ChevronRight size={11} />)}
          <Wrench size={11} className="chat-step-icon" />
          <span className="chat-step-label">{label}</span>
        </button>
        <AnimatePresence initial={false}>
          {expanded && hasResult && (
            <motion.div
              className="chat-step-content chat-step-observation"
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.2 }}
            >
              <div className="chat-step-observation-label">
                <Eye size={10} />
                <span>Kết quả</span>
              </div>
              <pre className="chat-step-result">{step.result}</pre>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}

