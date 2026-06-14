'use client'

import { memo, useMemo } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { marked } from 'marked'

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
    return <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
  },
  (prev, next) => prev.content === next.content,
)

/**
 * Memoized, block-level markdown renderer for streaming chat answers.
 * Stable earlier blocks are skipped by React.memo with zero work; only the
 * block currently being written re-renders.
 */
export const MarkdownMessage = memo(function MarkdownMessage({ content }: { content: string }) {
  const blocks = useMemo(() => splitBlocks(content), [content])
  return (
    <>
      {blocks.map((block, i) => (
        <MarkdownBlock key={i} content={block} />
      ))}
    </>
  )
})
