'use client'

import { memo, useEffect, useRef } from 'react'

import { colorVarToRgb, cssVar } from '@/lib/cssColor'

/** Base CSS injected into the iframe: theme tokens (resolved to rgb) + resets. */
function baseStyle(): string {
  const v = colorVarToRgb
  return (
    ':root{'
    + `--text:${v('--text-primary', 'rgb(20,20,22)')};`
    + `--muted:${v('--text-tertiary', 'rgb(120,120,130)')};`
    + `--accent:${v('--accent-green', 'rgb(0,179,134)')};`
    + `--border:${v('--surface-border', 'rgba(128,128,128,0.2)')};`
    + `--card:${v('--bg-elevated', 'rgb(255,255,255)')};}`
    + 'html,body{margin:0;background:transparent;color:var(--text);'
    + `font-family:${cssVar('--font-sans', 'system-ui,sans-serif')};`
    + 'font-size:14px;line-height:1.5;}*{box-sizing:border-box;}#__c{padding:4px;}'
  )
}

/**
 * Renders a ```visual block (plain HTML/CSS/SVG the model wrote) and — unlike a
 * React artifact — STREAMS it in: as more HTML arrives, the iframe's container
 * innerHTML grows and the browser paints the new content, so a card/timeline
 * builds up live (this is the native incremental HTML rendering Claude uses for
 * its streaming visuals).
 *
 * Security: `sandbox="allow-same-origin"` WITHOUT `allow-scripts` — JS never
 * runs inside (no XSS, inline handlers and javascript: are inert), while the
 * same-origin grant lets the parent write the HTML and read scrollHeight for
 * auto-sizing. Verified in real Chrome.
 */
function HtmlArtifact({ html }: { html: string }) {
  const ref = useRef<HTMLIFrameElement>(null)

  function paint() {
    const iframe = ref.current
    const doc = iframe?.contentDocument
    if (!iframe || !doc) return
    if (!doc.getElementById('__base')) {
      doc.open()
      doc.write(
        '<!doctype html><html><head><style id="__base">'
        + baseStyle()
        + '</style></head><body><div id="__c"></div></body></html>',
      )
      doc.close()
    }
    const container = doc.getElementById('__c')
    if (container) container.innerHTML = html
    const h = Math.min(2400, Math.max(40, (doc.body?.scrollHeight ?? 40) + 10))
    iframe.style.height = `${h}px`
  }

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(paint, [html])

  return (
    <div className="chat-artifact">
      <iframe ref={ref} title="visual" sandbox="allow-same-origin" onLoad={paint} />
    </div>
  )
}

export const ChatHtmlArtifact = memo(HtmlArtifact, (prev, next) => prev.html === next.html)
