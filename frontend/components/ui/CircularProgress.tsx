import { motion } from 'framer-motion'

export function CircularProgress({ pct, color, icon, size = 80 }: { pct: number; color: string; icon: string; size?: number }) {
  const r = (size - 12) / 2
  const circ = 2 * Math.PI * r
  const filled = circ * (pct / 100)

  return (
    <div style={{ position: 'relative', width: size, height: size, flexShrink: 0 }}>
      <svg width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--surface-border)" strokeWidth={8} />
        <motion.circle
          cx={size / 2} cy={size / 2} r={r} fill="none"
          stroke={color} strokeWidth={8}
          strokeLinecap="round"
          strokeDasharray={circ}
          initial={{ strokeDashoffset: circ }}
          animate={{ strokeDashoffset: circ - filled }}
          transition={{ duration: 1.2, ease: 'easeOut', delay: 0.2 }}
        />
      </svg>
      <div style={{
        position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center',
      }}>
        <span style={{ fontSize: size / 4 }}>{icon}</span>
        <span style={{ fontSize: 11, fontWeight: 700, color }}>{pct.toFixed(0)}%</span>
      </div>
    </div>
  )
}
