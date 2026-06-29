'use client'

import { memo, useEffect, useRef, useState } from 'react'

import { CHART_COLORS } from '@/lib/chartTheme'
import { colorVarToRgb, cssVar as token } from '@/lib/cssColor'

let _seq = 0

/**
 * Repair the single most common model mistake in Mermaid `timeline`/`mindmap`:
 * writing a period's extra notes as continuation lines that START with ":"
 * (`2024 : role` / newline / `: note`). Mermaid only accepts multiple events on
 * the SAME line (`2024 : role : note`), so we merge any line whose first
 * non-space char is ":" into the line above. Applied ONLY after the raw source
 * fails to parse, so valid diagrams are never touched. A line can only legally
 * begin with ":" in this broken form (flowchart/sequence put ":" mid-line), so
 * the transform is safe across diagram types.
 */
function repairMermaidSource(code: string): string {
  const lines = code.split('\n')
  const out: string[] = []
  for (const line of lines) {
    if (/^\s*:/.test(line) && out.length > 0) {
      out[out.length - 1] = `${out[out.length - 1].replace(/\s+$/, '')} ${line.trim()}`
    } else {
      out.push(line)
    }
  }
  return out.join('\n')
}

/**
 * Renders a ```mermaid block into a real SVG diagram — flowchart, timeline,
 * sequence, mindmap, state, ER… — so the agent never falls back to ASCII art
 * for structural/sequential visuals (quantitative data still uses ChatChart).
 *
 * - Themed to the app's design tokens (transparent bg, token colors + fonts).
 * - Sanitized: securityLevel 'strict' (DOMPurify on the model-generated SVG).
 * - Streaming-safe: a half-written diagram won't parse, so we keep a quiet
 *   "Đang dựng sơ đồ…" placeholder WHILE the source is still arriving; only once
 *   it stops changing and still won't parse do we fall back to showing the raw
 *   source (never an eternal spinner, never lost information).
 * - Memoized by source so a finished diagram stops re-rendering as later tokens
 *   stream in (mirrors ChartBlock).
 */
function MermaidDiagram({ code }: { code: string }) {
  const [svg, setSvg] = useState<string | null>(null)
  const [failed, setFailed] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const idRef = useRef(`mmd-${(_seq += 1)}`)

  useEffect(() => {
    let cancelled = false
    let failTimer: ReturnType<typeof setTimeout> | undefined
    setFailed(false)

    void (async () => {
      let reason = 'cú pháp không hợp lệ'
      try {
        const mermaid = (await import('mermaid')).default
        mermaid.initialize({
          startOnLoad: false,
          securityLevel: 'strict',
          theme: 'base',
          fontFamily: token('--font-sans', 'system-ui, sans-serif'),
          themeVariables: {
            background: 'transparent',
            primaryColor: colorVarToRgb('--bg-subtle', 'rgb(244, 244, 245)'),
            primaryBorderColor: CHART_COLORS.green,
            primaryTextColor: colorVarToRgb('--text-primary', 'rgb(17, 17, 17)'),
            secondaryColor: colorVarToRgb('--bg-elevated', 'rgb(255, 255, 255)'),
            tertiaryColor: colorVarToRgb('--bg-subtle', 'rgb(244, 244, 245)'),
            lineColor: colorVarToRgb('--text-tertiary', 'rgb(156, 163, 175)'),
            textColor: colorVarToRgb('--text-primary', 'rgb(17, 17, 17)'),
            fontSize: '14px',
          },
        })

        // parse() with suppressErrors returns false instead of throwing — lets us
        // tell "not valid YET" (still streaming) from a definitive syntax error.
        let source = code.trim()
        let valid = Boolean(await mermaid.parse(source, { suppressErrors: true }))
        if (!valid) {
          // Try the common-mistake repair before giving up.
          const repaired = repairMermaidSource(source)
          if (repaired !== source && (await mermaid.parse(repaired, { suppressErrors: true }))) {
            source = repaired
            valid = true
          }
        }
        if (cancelled) return
        if (valid) {
          // render() can still throw (a measurement/label issue parse doesn't catch).
          const { svg: rendered } = await mermaid.render(idRef.current, source)
          if (!cancelled) setSvg(rendered)
          return
        }
      } catch (e) {
        reason = e instanceof Error ? e.message : String(e)
      }
      // Might just be mid-stream; only surface the fallback (with the real reason)
      // if this source stops changing — i.e. this effect isn't superseded — for a beat.
      if (!cancelled) {
        failTimer = setTimeout(() => {
          if (cancelled) return
          setErr(reason)
          setFailed(true)
        }, 700)
      }
    })()

    return () => {
      cancelled = true
      if (failTimer) clearTimeout(failTimer)
    }
  }, [code])

  if (svg) {
    return <div className="chat-mermaid" dangerouslySetInnerHTML={{ __html: svg }} />
  }
  if (failed) {
    return (
      <div className="chat-mermaid-fallback">
        <span className="chat-mermaid-fallback-note">
          Sơ đồ không dựng được{err ? ` — ${err.slice(0, 160)}` : ''}. Nguồn:
        </span>
        <pre>{code.trim()}</pre>
      </div>
    )
  }
  return <div className="chat-chart-loading">Đang dựng sơ đồ…</div>
}

export const ChatMermaid = memo(MermaidDiagram, (prev, next) => prev.code === next.code)
