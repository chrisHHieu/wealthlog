'use client'

import { memo, useMemo, type ReactNode } from 'react'
import ReactMarkdown, { type Components } from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { marked } from 'marked'
import { ChatArtifact } from '@/components/chat/ChatArtifact'
import { ChatChart, parseChartSpec } from '@/components/chat/ChatChart'
import { ChatHtmlArtifact } from '@/components/chat/ChatHtmlArtifact'
import { ChatMermaid } from '@/components/chat/ChatMermaid'

/** Plain-text content of a node, for detecting numeric citation links. */
function textOf(children: ReactNode): string {
  if (typeof children === 'string') return children
  if (Array.isArray(children)) return children.map(textOf).join('')
  return ''
}

/**
 * Links render in a new tab; a link whose visible text is just a number (from
 * linkifyCitations turning `[n]` into `[n](url)`) renders as a small citation
 * chip instead.
 */
const MARKDOWN_COMPONENTS: Components = {
  a({ href, title, children }) {
    const label = textOf(children).trim()
    const isCitation = /^\d+$/.test(label)
    return (
      <a
        href={href}
        title={title}
        target="_blank"
        rel="noopener noreferrer"
        className={isCitation ? 'chat-cite' : undefined}
      >
        {children}
      </a>
    )
  },
}

/**
 * Split markdown into top-level blocks (paragraphs, code fences, tables, lists…)
 * using marked's lexer. Each block's `raw` source is a self-contained chunk we
 * can parse and memoize independently — so while streaming, only the final
 * (growing) block re-parses on each token instead of the whole document.
 *
 * Re-parsing the entire accumulated markdown every token is O(n) per token →
 * O(n²) over a message, which is what makes long answers visibly slow.
 */
function splitBlocks(markdown: string): string[] {
  try {
    return marked.lexer(markdown).map(token => token.raw)
  } catch {
    // marked should never throw on partial markdown, but never let the chat
    // crash mid-stream — fall back to one block.
    return [markdown]
  }
}

const MarkdownBlock = memo(
  function MarkdownBlock({ content }: { content: string }) {
    return (
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={MARKDOWN_COMPONENTS}>
        {content}
      </ReactMarkdown>
    )
  },
  (prev, next) => prev.content === next.content,
)

/**
 * Memoized, block-level markdown renderer for streaming chat answers.
 * Stable earlier blocks are skipped by React.memo with zero work; only the
 * block currently being written re-renders.
 */
/** Pull the JSON body out of a ```chart fence (closing fence optional mid-stream). */
function chartBody(block: string): string | null {
  const t = block.trim()
  if (!t.startsWith('```chart')) return null
  return t.replace(/^```chart[^\n]*\n?/, '').replace(/\n?```$/, '')
}

/** Pull the source out of a ```mermaid fence (closing fence optional mid-stream). */
function mermaidBody(block: string): string | null {
  const t = block.trim()
  if (!t.startsWith('```mermaid')) return null
  return t.replace(/^```mermaid[^\n]*\n?/, '').replace(/\n?```$/, '')
}

/**
 * Pull a ```visual fence's HTML. No completeness gate: a ```visual streams in
 * progressively (the browser paints growing HTML natively), so we render its
 * partial body on every tick — a card/timeline builds up live.
 */
function visualBody(block: string): string | null {
  const t = block.trim()
  if (!t.startsWith('```visual')) return null
  return t.replace(/^```visual[^\n]*\n?/, '').replace(/\n?```$/, '')
}

/**
 * Pull a ```artifact fence's React source (partial while streaming). ChatArtifact
 * streams each update into a persistent iframe and renders it progressively, so
 * there's no completeness gate — it builds up live as the code arrives.
 */
function artifactBody(block: string): string | null {
  const t = block.trim()
  if (!t.startsWith('```artifact')) return null
  return t.replace(/^```artifact[^\n]*\n?/, '').replace(/\n?```$/, '')
}

/**
 * Memoized by the JSON body string, so once a chart's spec is fully streamed the
 * block stops re-rendering — without this, every later streaming tick re-parses
 * and remounts the chart, restarting Recharts' animation so it shows an empty
 * frame until the whole message finishes.
 */
const ChartBlock = memo(function ChartBlock({ body }: { body: string }) {
  const spec = parseChartSpec(body)
  return spec
    ? <ChatChart spec={spec} />
    : <div className="chat-chart-loading">Đang dựng biểu đồ…</div>
})

export const MarkdownMessage = memo(function MarkdownMessage({ content }: { content: string }) {
  const blocks = useMemo(() => splitBlocks(content), [content])
  return (
    <>
      {blocks.map((block, i) => {
        const chart = chartBody(block)
        if (chart !== null) return <ChartBlock key={i} body={chart} />
        const visual = visualBody(block)
        if (visual !== null) return <ChatHtmlArtifact key={i} html={visual} />
        const artifact = artifactBody(block)
        if (artifact !== null) return <ChatArtifact key={i} code={artifact} />
        const mermaid = mermaidBody(block)
        if (mermaid !== null) return <ChatMermaid key={i} code={mermaid} />
        return <MarkdownBlock key={i} content={block} />
      })}
    </>
  )
})
