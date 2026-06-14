'use client'

import { useEffect, useRef, useState } from 'react'

/**
 * Smooth streaming: reveal `text` at a steady cadence instead of painting
 * whatever arrived in the last frame. Anthropic streams multi-token deltas, so
 * rendering them raw jumps in bursts; dripping characters out on a rAF clock
 * gives the buttery token-by-token feel of ChatGPT/Claude.
 *
 * - The reveal rate adapts to the backlog (`remaining`), so a fast stream never
 *   lags far behind — it speeds up to catch the buffer, then settles.
 * - When `text` stops growing, the reveal catches up and the loop stops.
 * - Non-streaming text (persisted history, error fallbacks) shows instantly:
 *   only messages that were ever streaming animate.
 *
 * One ChatMessage instance per message id (the list keys by id), so `text` only
 * ever grows for a given hook — no cross-message reset logic is needed.
 */
export function useSmoothText(text: string, streaming: boolean): string {
  // Latch: a message that streamed even once keeps animating its tail to the
  // end; one that never streamed (persisted) renders in full immediately.
  const everStreamedRef = useRef(streaming)
  if (streaming) everStreamedRef.current = true
  const animate = everStreamedRef.current

  const [shown, setShown] = useState(animate ? 0 : text.length)

  const shownRef = useRef(shown)
  shownRef.current = shown
  const targetRef = useRef(text.length)
  targetRef.current = text.length
  const rafRef = useRef<number | null>(null)
  const lastTickRef = useRef(0)

  useEffect(() => {
    if (!animate) {
      // Non-streaming: stay fully in sync (covers the rare grow-after-load case).
      if (shownRef.current !== text.length) setShown(text.length)
      return
    }
    if (shownRef.current >= targetRef.current) return
    if (rafRef.current != null) return // a loop is already running; it reads refs

    const tick = (now: number) => {
      const last = lastTickRef.current || now
      const dt = Math.min(now - last, 100) // clamp after tab-switch stalls
      lastTickRef.current = now

      const target = targetRef.current
      const remaining = target - shownRef.current
      // Base reading cadence + proportional catch-up so the visible text never
      // trails the stream by more than a beat.
      const charsPerSec = 80 + remaining * 10
      const next = Math.min(target, shownRef.current + Math.max(1, (charsPerSec * dt) / 1000))
      const nextInt = Math.ceil(next)
      shownRef.current = nextInt
      setShown(nextInt)

      if (nextInt < targetRef.current) {
        rafRef.current = requestAnimationFrame(tick)
      } else {
        rafRef.current = null
        lastTickRef.current = 0
      }
    }
    rafRef.current = requestAnimationFrame(tick)
  }, [text, animate])

  // Cancel on unmount only — the loop self-sustains across token re-renders.
  useEffect(() => () => {
    if (rafRef.current != null) cancelAnimationFrame(rafRef.current)
  }, [])

  return animate ? text.slice(0, shown) : text
}
