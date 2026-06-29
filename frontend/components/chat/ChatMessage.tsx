'use client'

import { motion, AnimatePresence } from 'framer-motion'
import {
  ChevronDown, ChevronRight, Check, Copy, Brain, Wrench,
  MessageSquare, AlertCircle, RotateCcw, Sparkles,
  ShieldAlert, X, Loader2, Globe, FileText,
} from 'lucide-react'
import { memo, useEffect, useRef, useState } from 'react'
import Image from 'next/image'
import { useQueryClient } from '@tanstack/react-query'
import { cn } from '@/lib/utils'
import { apiJson } from '@/lib/api'
import { MarkdownMessage } from '@/components/chat/MarkdownMessage'
import { useSmoothText } from '@/hooks/useSmoothText'
import {
  citedFooterSources, collectWebSources, faviconUrl, linkifyCitations, type WebSource,
} from '@/lib/webSources'
import type { ActionStatus, ChatMessage as ChatMessageType, ChatStep } from '@/types/chat'

const TOOL_LABELS: Record<string, string> = {
  // Reports
  get_financial_summary:        'View financial overview',
  get_spending_trends:          'Analyze spending trends',
  get_top_expenses:             'View top expenses',
  get_upcoming_bills:           'Check upcoming bills',
  // Transactions
  search_transactions:          'Search transactions',
  get_spending_by_category:     'View spending by category',
  get_income_by_category:       'View income by category',
  create_transaction:           'Create transaction',
  create_multiple_transactions: 'Create multiple transactions',
  update_transaction:           'Update transaction',
  update_multiple_transactions: 'Update multiple transactions',
  delete_transaction:           'Delete transaction',
  delete_multiple_transactions: 'Delete multiple transactions',
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
  // Web
  web_search:                   'Search the web',
  web_extract:                  'Read web page',
}

/** Tool-specific icon for the timeline step header (default: Wrench). */
function toolIcon(name: string) {
  if (name === 'web_search') return Globe
  if (name === 'web_extract') return FileText
  return Wrench
}

/** Live, human label for a tool step — web tools surface their target inline. */
function toolStepLabel(step: Extract<ChatStep, { kind: 'tool' }>): string {
  const base = TOOL_LABELS[step.name] ?? step.name
  if (step.name === 'web_search' && typeof step.input?.query === 'string') {
    return `Searching “${step.input.query}”`
  }
  if (step.name === 'web_extract' && typeof step.input?.url === 'string') {
    try {
      return `Reading ${new URL(step.input.url).hostname.replace(/^www\./, '')}`
    } catch { /* fall through to base label */ }
  }
  return base
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

  // Deferred financial writes that need explicit user sign-off, surfaced as
  // prominent cards (never buried inside the collapsed work trail).
  const confirmSteps = steps.filter(
    (s): s is Extract<ChatStep, { kind: 'tool' }> => s.kind === 'tool' && !!s.pendingActionId,
  )

  // Show pending dots only before ANY event has arrived (no content, no steps).
  const showPendingDots = message.isStreaming && steps.length === 0 && !message.content

  // Web sources cited across the whole message — power inline [n] chips + footer.
  const webSources = collectWebSources(steps)
  // The footer shows only the sources the answer actually cites (not every raw
  // search hit), so it matches the inline chips.
  const answerText = finalAnswer?.content ?? fallbackContent ?? ''
  const footerSources = citedFooterSources(answerText, webSources)

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
          <FinalAnswer step={finalAnswer} sources={webSources} />
        )}

        {fallbackContent && (
          <div className="chat-md">
            <MarkdownMessage content={linkifyCitations(fallbackContent, webSources)} />
          </div>
        )}

        {/* Sources footer — clickable cards for the sources the answer cited */}
        {!message.isStreaming && footerSources.length > 0 && (
          <Sources sources={footerSources} />
        )}

        {confirmSteps.map(step => (
          <PendingActionCard key={step.id} step={step} />
        ))}

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
function FinalAnswer({ step, sources }: {
  step: Extract<ChatStep, { kind: 'text' }>
  sources: WebSource[]
}) {
  const smooth = useSmoothText(step.content, !!step.streaming)
  const content = linkifyCitations(smooth, sources)

  return (
    <div className={cn('chat-md', step.streaming && 'chat-md--live')}>
      {content ? (
        <MarkdownMessage content={content} />
      ) : (
        <div className="chat-inline-dots" aria-label="Processing">
          <span /><span /><span />
        </div>
      )}
    </div>
  )
}

/** One web source as a favicon + title + domain card linking out in a new tab. */
function SourceCard({ source, index }: { source: WebSource; index: number }) {
  const [iconFailed, setIconFailed] = useState(false)
  return (
    <a
      className="chat-source-card"
      href={source.url}
      target="_blank"
      rel="noopener noreferrer"
      title={source.title}
    >
      <span className="chat-source-index">{index}</span>
      {iconFailed ? (
        <Globe size={13} className="chat-source-favicon-fallback" />
      ) : (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          className="chat-source-favicon"
          src={faviconUrl(source.domain)}
          alt=""
          width={14}
          height={14}
          onError={() => setIconFailed(true)}
        />
      )}
      <span className="chat-source-text">
        <span className="chat-source-title">{source.title}</span>
        <span className="chat-source-domain">{source.domain}</span>
      </span>
    </a>
  )
}

/** "Sources" section under the answer — one card per cited web source. */
function Sources({ sources }: { sources: WebSource[] }) {
  return (
    <div className="chat-sources">
      <div className="chat-sources-head">
        <Globe size={11} />
        <span>Sources</span>
      </div>
      <div className="chat-sources-list">
        {sources.map((source, i) => (
          <SourceCard key={source.url} source={source} index={source.num ?? i + 1} />
        ))}
      </div>
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

const ACTION_STATUS_LABELS: Record<ActionStatus, string> = {
  pending: '',
  executed: 'Confirmed',
  rejected: 'Rejected',
  failed: 'Failed',
}

function formatParamValue(key: string, value: unknown): string {
  if (key === 'amount' && (typeof value === 'number' || typeof value === 'string')) {
    const n = Number(value)
    if (Number.isFinite(n)) return `${n.toLocaleString('en-US')} VND`
  }
  return typeof value === 'object' ? JSON.stringify(value) : String(value)
}

/**
 * Confirmation card for a financial write the agent deferred. Mirrors Claude
 * Code's permission prompt: show the action + its inputs, then Confirm / Reject.
 * The write only runs when the user confirms (POST .../confirm); rejecting
 * discards it. Self-contained — resolves via the API and tracks its own state.
 */
// Query families to refresh after a write actually lands, so other views
// (transactions list, dashboard, accounts) reflect it without a manual reload.
const INVALIDATE_ON_WRITE = ['transactions', 'dashboard', 'accounts', 'reports', 'budgets']

function ConfirmItem({ item }: { item: { label: string; detail?: string } }) {
  return (
    <div className="chat-confirm-item">
      <span className="chat-confirm-item-label">{item.label}</span>
      {item.detail && <span className="chat-confirm-item-detail">{item.detail}</span>}
    </div>
  )
}

function PendingActionCard({ step }: { step: Extract<ChatStep, { kind: 'tool' }> }) {
  const [status, setStatus] = useState<ActionStatus>(step.actionStatus ?? 'pending')
  const [busy, setBusy] = useState<null | 'confirm' | 'reject'>(null)
  const [receipt, setReceipt] = useState<string | null>(null)
  const [expanded, setExpanded] = useState(false)
  const queryClient = useQueryClient()
  const label = TOOL_LABELS[step.name] ?? step.name
  const input = step.input || {}
  const preview = step.preview
  const pending = status === 'pending'

  const resolve = async (action: 'confirm' | 'reject') => {
    if (busy) return
    setBusy(action)
    try {
      const res = await apiJson<{ ok: boolean; result?: string }>(
        `/api/chat/actions/${step.pendingActionId}/${action}`,
        { method: 'POST' },
      )
      const next: ActionStatus = action === 'confirm' ? (res.ok ? 'executed' : 'failed') : 'rejected'
      setStatus(next)
      setReceipt(res.result ?? null)
      // Only refresh data when the write truly succeeded.
      if (next === 'executed') {
        INVALIDATE_ON_WRITE.forEach(key => queryClient.invalidateQueries({ queryKey: [key] }))
      }
    } catch {
      // 409 (already resolved) or network error — clear the stale prompt; the
      // reload path reconciles the true status from the server.
      setStatus(action === 'confirm' ? 'failed' : 'rejected')
    } finally {
      setBusy(null)
    }
  }

  const failed = status === 'failed'

  return (
    <div className={cn('chat-confirm', `chat-confirm--${status}`)}>
      <div className="chat-confirm-head">
        <ShieldAlert size={14} className="chat-confirm-icon" />
        <span className="chat-confirm-title">{label}</span>
        {!pending && <span className="chat-confirm-badge">{ACTION_STATUS_LABELS[status]}</span>}
      </div>

      {pending && (
        <p className="chat-confirm-note">Review and confirm before this is saved.</p>
      )}

      {preview ? (
        <div className="chat-confirm-preview">
          <p className="chat-confirm-summary">{preview.summary}</p>
          {preview.items.length === 1 ? (
            <ConfirmItem item={preview.items[0]} />
          ) : preview.items.length > 1 && (
            <>
              <button
                type="button"
                className="chat-confirm-toggle"
                onClick={() => setExpanded(e => !e)}
              >
                {expanded ? 'Hide details' : `Show ${preview.items.length} transactions`}
              </button>
              {expanded && (
                <div className="chat-confirm-items">
                  {preview.items.map((it, i) => <ConfirmItem key={i} item={it} />)}
                </div>
              )}
            </>
          )}
        </div>
      ) : Object.keys(input).length > 0 && (
        <div className="chat-confirm-params">
          {Object.entries(input).map(([k, v]) => (
            <div key={k} className="chat-confirm-row">
              <span className="chat-confirm-key">{k}</span>
              <span className={cn('chat-confirm-val', k === 'amount' && 'chat-confirm-val--amount')}>
                {formatParamValue(k, v)}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Action receipt: the real tool outcome (created row / error), not just a badge. */}
      {receipt && (
        <p className={cn('chat-confirm-receipt', failed && 'chat-confirm-receipt--error')}>
          {receipt}
        </p>
      )}

      {pending && (
        <div className="chat-confirm-actions">
          <button
            className="chat-confirm-btn chat-confirm-btn--reject"
            onClick={() => resolve('reject')}
            disabled={!!busy}
          >
            {busy === 'reject' ? <Loader2 size={13} className="chat-confirm-spin" /> : <X size={13} />}
            <span>Reject</span>
          </button>
          <button
            className="chat-confirm-btn chat-confirm-btn--confirm"
            onClick={() => resolve('confirm')}
            disabled={!!busy}
          >
            {busy === 'confirm' ? <Loader2 size={13} className="chat-confirm-spin" /> : <Check size={13} />}
            <span>Confirm</span>
          </button>
        </div>
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
  const label = toolStepLabel(step)
  const isError = step.status === 'error'
  const isRunning = step.status === 'running'
  const StepIcon = toolIcon(step.name)
  // Web tools: render the result as clickable source rows, not a raw text dump.
  const stepSources = hasResult ? collectWebSources([step]) : []

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
          <StepIcon size={11} className="chat-step-icon" />
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
                    <span>{stepSources.length > 0 ? 'Sources' : 'Result'}</span>
                  </div>
                  {stepSources.length > 0 ? (
                    <div className="chat-step-sources">
                      {stepSources.map((source, i) => (
                        <SourceCard key={source.url} source={source} index={source.num ?? i + 1} />
                      ))}
                    </div>
                  ) : (
                    <pre className="chat-step-result">{step.result}</pre>
                  )}
                </>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}
