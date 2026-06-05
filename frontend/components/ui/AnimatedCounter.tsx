'use client'

import { useEffect, useRef, useState } from 'react'

interface AnimatedCounterProps {
  value: number
  duration?: number
  format?: (value: number) => string
  className?: string
  style?: React.CSSProperties
}

export function AnimatedCounter({
  value,
  duration = 1200,
  format = (v) => v.toLocaleString('en-US'),
  className,
  style,
}: AnimatedCounterProps) {
  const [displayValue, setDisplayValue] = useState(0)
  const prevValue = useRef(0)
  const rafRef = useRef<number>(null)

  useEffect(() => {
    const start = prevValue.current
    const end = value
    const startTime = performance.now()

    function easeOutCubic(t: number) {
      return 1 - Math.pow(1 - t, 3)
    }

    function update(now: number) {
      const elapsed = now - startTime
      const progress = Math.min(elapsed / duration, 1)
      const easedProgress = easeOutCubic(progress)
      const current = start + (end - start) * easedProgress
      setDisplayValue(current)

      if (progress < 1) {
        rafRef.current = requestAnimationFrame(update)
      } else {
        prevValue.current = end
      }
    }

    if (rafRef.current) cancelAnimationFrame(rafRef.current)
    rafRef.current = requestAnimationFrame(update)

    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current)
    }
  }, [value, duration])

  return (
    <span className={className} style={style}>
      {format(displayValue)}
    </span>
  )
}
