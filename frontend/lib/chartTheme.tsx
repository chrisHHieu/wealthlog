/**
 * Centralized chart theming for Recharts
 * Premium styling with gradients, custom colors, and consistent formatting
 */

export const CHART_COLORS = {
  green: '#00B386',
  greenLight: '#00D4A0',
  gold: '#E8A838',
  goldLight: '#F0BE5A',
  red: '#F04770',
  redLight: '#FF6B8A',
  blue: '#3B82F6',
  blueLight: '#60A5FA',
  purple: '#8B5CF6',
  purpleLight: '#A78BFA',
  amber: '#F59E0B',
  cyan: '#06B6D4',
  pink: '#EC4899',
  teal: '#14B8A6',
}

export const CHART_CATEGORY_COLORS = [
  CHART_COLORS.green,
  CHART_COLORS.blue,
  CHART_COLORS.gold,
  CHART_COLORS.purple,
  CHART_COLORS.red,
  CHART_COLORS.cyan,
  CHART_COLORS.pink,
  CHART_COLORS.teal,
  CHART_COLORS.amber,
]

export const AXIS_STYLE = {
  fontSize: 11,
  fontFamily: 'var(--font-sans)',
  fill: 'var(--text-tertiary)',
}

export const GRID_STYLE = {
  stroke: 'var(--surface-border)',
  strokeDasharray: '3 3',
  strokeOpacity: 0.6,
}

export const TOOLTIP_STYLE = {
  contentStyle: {
    background: 'var(--bg-elevated)',
    border: '1px solid var(--surface-border)',
    borderRadius: 'var(--radius-md)',
    backdropFilter: 'blur(16px)',
    boxShadow: 'var(--elevation-3)',
    padding: '12px 16px',
    fontSize: 13,
    lineHeight: 1.5,
    color: 'var(--text-primary)',
  },
  cursor: {
    stroke: 'var(--text-tertiary)',
    strokeWidth: 1,
    strokeDasharray: '4 4',
  },
  itemStyle: {
    padding: '2px 0',
    fontSize: 12,
    color: 'var(--text-secondary)',
  },
  labelStyle: {
    fontWeight: 600,
    fontSize: 12,
    color: 'var(--text-primary)',
    marginBottom: 4,
  },
}

// Gradient definitions for use in charts
export function GradientDefs() {
  return (
    <>
      <linearGradient id="gradientGreen" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stopColor={CHART_COLORS.green} stopOpacity={1} />
        <stop offset="100%" stopColor={CHART_COLORS.green} stopOpacity={0.2} />
      </linearGradient>
      <linearGradient id="gradientGold" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stopColor={CHART_COLORS.gold} stopOpacity={1} />
        <stop offset="100%" stopColor={CHART_COLORS.gold} stopOpacity={0.2} />
      </linearGradient>
      <linearGradient id="gradientRed" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stopColor={CHART_COLORS.red} stopOpacity={1} />
        <stop offset="100%" stopColor={CHART_COLORS.red} stopOpacity={0.2} />
      </linearGradient>
      <linearGradient id="gradientBlue" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stopColor={CHART_COLORS.blue} stopOpacity={1} />
        <stop offset="100%" stopColor={CHART_COLORS.blue} stopOpacity={0.2} />
      </linearGradient>
      <linearGradient id="gradientPurple" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stopColor={CHART_COLORS.purple} stopOpacity={1} />
        <stop offset="100%" stopColor={CHART_COLORS.purple} stopOpacity={0.2} />
      </linearGradient>
      <linearGradient id="areaGreen" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stopColor={CHART_COLORS.green} stopOpacity={0.3} />
        <stop offset="100%" stopColor={CHART_COLORS.green} stopOpacity={0} />
      </linearGradient>
      <linearGradient id="areaGold" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stopColor={CHART_COLORS.gold} stopOpacity={0.3} />
        <stop offset="100%" stopColor={CHART_COLORS.gold} stopOpacity={0} />
      </linearGradient>
    </>
  )
}
