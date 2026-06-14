'use client'

import { useId } from 'react'

interface SparklineProps {
  data: number[]
  height?: number
  stroke?: string
  /** Optional area fill under the line; defaults to a fade of the stroke color. */
  fill?: boolean
}

/**
 * Dependency-free SVG sparkline. Stretches to its container width via
 * viewBox + preserveAspectRatio, so it stays crisp at any size.
 */
export function Sparkline({ data, height = 40, stroke = 'var(--accent-green)', fill = true }: SparklineProps) {
  const gradientId = useId()

  if (data.length < 2) return null

  const W = 100
  const H = 100
  const PAD = 6
  const min = Math.min(...data)
  const max = Math.max(...data)
  const range = max - min || 1

  const points = data.map((v, i) => ({
    x: (i / (data.length - 1)) * W,
    y: PAD + (1 - (v - min) / range) * (H - PAD * 2),
  }))

  const linePath = points
    .map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x.toFixed(2)},${p.y.toFixed(2)}`)
    .join(' ')
  const areaPath = `${linePath} L${W},${H} L0,${H} Z`

  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      preserveAspectRatio="none"
      style={{ width: '100%', height, display: 'block' }}
      aria-hidden="true"
    >
      {fill && (
        <>
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={stroke} stopOpacity="0.18" />
              <stop offset="100%" stopColor={stroke} stopOpacity="0" />
            </linearGradient>
          </defs>
          <path d={areaPath} fill={`url(#${gradientId})`} />
        </>
      )}
      <path
        d={linePath}
        fill="none"
        stroke={stroke}
        strokeWidth="2"
        strokeLinejoin="round"
        strokeLinecap="round"
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  )
}
