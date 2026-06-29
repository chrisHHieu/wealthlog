'use client'

import { Component, type ReactElement, type ReactNode } from 'react'
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, LabelList, Line,
  LineChart, Pie, PieChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import { AXIS_STYLE, CHART_CATEGORY_COLORS, CHART_COLORS, GRID_STYLE } from '@/lib/chartTheme'
import type { ChartTooltipProps } from '@/types/chart'

interface RefLine {
  value: number
  label?: string
  color?: string
}

/** Declarative chart spec the agent emits inside a ```chart code fence. */
export interface ChartSpec {
  type: 'bar' | 'line' | 'area' | 'pie'
  title?: string
  /** Each row: a `label` (category/x) + numeric series field(s); a single-series
   *  row may also carry `highlight: true` and/or `color` (a named token). */
  data: Array<Record<string, string | number | boolean>>
  /** Numeric field names to plot; inferred from the data when omitted. */
  series?: string[]
  /** Optional unit appended to values (e.g. "triệu", "%"). */
  unit?: string
  /** Optional per-series colors (named tokens: green/gold/red/blue/purple/…). */
  colors?: string[]
  /** Optional target/reference line(s) on bar/line/area charts. */
  refLine?: RefLine | RefLine[]
}

const _TYPES = new Set(['bar', 'line', 'area', 'pie'])

/** Resolve a named color token to its theme hex; unknown → palette fallback. */
function resolveColor(name: string | undefined, fallbackIdx: number): string {
  if (name && name in CHART_COLORS) return CHART_COLORS[name as keyof typeof CHART_COLORS]
  return CHART_CATEGORY_COLORS[fallbackIdx % CHART_CATEGORY_COLORS.length]
}

type Row = Record<string, string | number | boolean>

/** Keep only well-formed rows: a string label + ≥1 finite numeric field. Junk
 *  fields (non-numeric series values, bad types) are dropped so a partially
 *  malformed spec still renders the valid parts instead of a broken chart. */
function sanitizeRows(data: unknown[]): Row[] {
  const out: Row[] = []
  for (const raw of data) {
    if (!raw || typeof raw !== 'object') continue
    const row: Row = {}
    let hasNumber = false
    for (const [k, v] of Object.entries(raw as Record<string, unknown>)) {
      if (k === 'label') row.label = String(v)
      else if (k === 'highlight') { if (v === true) row.highlight = true }
      else if (k === 'color') { if (typeof v === 'string') row.color = v }
      else if (typeof v === 'number' && Number.isFinite(v)) { row[k] = v; hasNumber = true }
    }
    if (!hasNumber) continue
    if (typeof row.label !== 'string') row.label = String(out.length + 1)
    out.push(row)
  }
  return out
}

function normalizeRefLine(rl: unknown): RefLine[] | undefined {
  const arr = Array.isArray(rl) ? rl : rl != null ? [rl] : []
  const out: RefLine[] = []
  for (const r of arr) {
    const x = r as RefLine
    if (r && typeof r === 'object' && typeof x.value === 'number' && Number.isFinite(x.value)) {
      out.push({
        value: x.value,
        label: typeof x.label === 'string' ? x.label : undefined,
        color: typeof x.color === 'string' ? x.color : undefined,
      })
    }
  }
  return out.length ? out : undefined
}

function isStringArray(v: unknown): v is string[] {
  return Array.isArray(v) && v.every(x => typeof x === 'string')
}

/** Parse + strictly validate/sanitize a chart spec; null on anything unusable. */
export function parseChartSpec(raw: string): ChartSpec | null {
  let obj: unknown
  try {
    obj = JSON.parse(raw)
  } catch {
    return null
  }
  if (!obj || typeof obj !== 'object') return null
  const s = obj as Record<string, unknown>
  if (typeof s.type !== 'string' || !_TYPES.has(s.type)) return null
  if (!Array.isArray(s.data)) return null
  const data = sanitizeRows(s.data)
  if (data.length === 0) return null
  return {
    type: s.type as ChartSpec['type'],
    title: typeof s.title === 'string' ? s.title : undefined,
    unit: typeof s.unit === 'string' ? s.unit : undefined,
    data,
    series: isStringArray(s.series) ? s.series : undefined,
    colors: isStringArray(s.colors) ? s.colors : undefined,
    refLine: normalizeRefLine(s.refLine),
  }
}

function seriesKeys(spec: ChartSpec): string[] {
  if (spec.series?.length) return spec.series
  const first = spec.data[0] ?? {}
  const numeric = Object.keys(first).filter(
    k => k !== 'label' && typeof first[k] === 'number',
  )
  return numeric.length ? numeric : ['value']
}

function fmtValue(v: number, unit?: string): string {
  const n = v.toLocaleString('en-US')
  return unit ? `${n} ${unit}` : n
}

/** Short value for on-bar labels, e.g. 140000 → "140K". */
function fmtCompact(v: number): string {
  return v.toLocaleString('en-US', { notation: 'compact', maximumFractionDigits: 1 })
}

const gradId = (i: number, kind: 'bar' | 'area') =>
  `cc-${kind}-${i % CHART_CATEGORY_COLORS.length}`

/** Vertical color→fade gradients so bars/areas read richer than a flat fill. */
function GradientDefs({ count, kind }: { count: number; kind: 'bar' | 'area' }) {
  const [top, bottom] = kind === 'area' ? [0.35, 0] : [1, 0.5]
  const n = Math.min(count, CHART_CATEGORY_COLORS.length)
  return (
    <defs>
      {Array.from({ length: n }).map((_, i) => (
        <linearGradient key={i} id={gradId(i, kind)} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={CHART_CATEGORY_COLORS[i]} stopOpacity={top} />
          <stop offset="100%" stopColor={CHART_CATEGORY_COLORS[i]} stopOpacity={bottom} />
        </linearGradient>
      ))}
    </defs>
  )
}

/** Tooltip passed to Recharts as an element (it injects active/payload/label). */
function ChartTip({ active, payload, label, unit }: ChartTooltipProps & { unit?: string }) {
  if (!active || !payload?.length) return null
  return (
    <div className="chart-tooltip">
      {label != null && label !== '' && (
        <div style={{ color: 'var(--text-secondary)', fontWeight: 600, marginBottom: 6, fontSize: 12 }}>
          {label}
        </div>
      )}
      {payload.map((p, i) => (
        <div key={p.dataKey ?? i} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 3 }}>
          <span style={{ width: 8, height: 8, borderRadius: 2, background: p.color, flexShrink: 0 }} />
          <span style={{ color: 'var(--text-secondary)', fontSize: 12 }}>{p.name}</span>
          <strong style={{ color: 'var(--text-primary)', fontSize: 12, marginLeft: 'auto', paddingLeft: 12 }}>
            {fmtValue(Number(p.value ?? 0), unit)}
          </strong>
        </div>
      ))}
    </div>
  )
}

interface LegendItem { name: string; color: string }

/** Legend rows: pie → one per slice; multi-series → one per series; else none. */
function legendItems(
  spec: ChartSpec, keys: string[], color: (i: number) => string,
): LegendItem[] {
  if (spec.type === 'pie') {
    return spec.data.map((d, i) => ({
      name: String(d.label ?? ''),
      color: typeof d.color === 'string' ? resolveColor(d.color, i) : color(i),
    }))
  }
  if (keys.length > 1) {
    return keys.map((k, i) => ({
      name: k,
      color: spec.colors?.[i] ? resolveColor(spec.colors[i], i) : color(i),
    }))
  }
  return []
}

/** Custom legend — a refined chip row, not Recharts' default block. */
function ChartLegend({ items }: { items: LegendItem[] }) {
  if (!items.length) return null
  return (
    <div className="chat-chart-legend">
      {items.map((it, i) => (
        <span key={i} className="chat-chart-legend-item">
          <span className="chat-chart-legend-dot" style={{ background: it.color }} />
          {it.name}
        </span>
      ))}
    </div>
  )
}

const _TYPE_LABEL = { bar: 'Bar', line: 'Line', area: 'Area', pie: 'Pie' } as const

/** A compact text version of the data — powers the aria-label and the fallback
 *  shown if Recharts ever fails to render. */
function dataSummary(spec: ChartSpec, keys: string[]): string {
  const single = keys.length === 1
  return spec.data
    .slice(0, 12)
    .map(d => {
      const label = String(d.label ?? '')
      return single
        ? `${label}: ${fmtValue(Number(d[keys[0]] ?? 0), spec.unit)}`
        : `${label} (${keys.map(k => `${k} ${fmtValue(Number(d[k] ?? 0), spec.unit)}`).join(', ')})`
    })
    .join('; ')
}

/** Render errors in Recharts shouldn't blank the answer — fall back to text. */
class ChartErrorBoundary extends Component<
  { fallback: ReactNode; children: ReactNode },
  { failed: boolean }
> {
  state = { failed: false }
  static getDerivedStateFromError() {
    return { failed: true }
  }
  render() {
    return this.state.failed ? this.props.fallback : this.props.children
  }
}

/** Render an agent-emitted chart spec as a luxury card with the app's theme. */
export function ChatChart({ spec }: { spec: ChartSpec }) {
  const keys = seriesKeys(spec)
  const tip = <ChartTip unit={spec.unit} />
  const color = (i: number) => CHART_CATEGORY_COLORS[i % CHART_CATEGORY_COLORS.length]
  const items = legendItems(spec, keys, color)
  const summary = dataSummary(spec, keys)
  const ariaLabel = `${_TYPE_LABEL[spec.type]} chart${spec.title ? `: ${spec.title}` : ''}. ${summary}`

  return (
    <figure className="chat-chart" role="img" aria-label={ariaLabel}>
      {(spec.title || items.length > 0) && (
        <header className="chat-chart-head">
          {spec.title && <figcaption className="chat-chart-title">{spec.title}</figcaption>}
          <ChartLegend items={items} />
        </header>
      )}
      <ChartErrorBoundary fallback={<p className="chat-chart-fallback">{summary}</p>}>
        <ResponsiveContainer width="100%" height={spec.type === 'pie' ? 240 : 280}>
          {renderChart(spec, keys, tip, color)}
        </ResponsiveContainer>
      </ChartErrorBoundary>
    </figure>
  )
}

function renderChart(
  spec: ChartSpec,
  keys: string[],
  tip: ReactElement,
  color: (i: number) => string,
) {
  // Per-series color: spec.colors override → solid token color, else gradient.
  const seriesColor = (i: number) =>
    spec.colors?.[i] ? resolveColor(spec.colors[i], i) : color(i)
  const refLines = spec.refLine
    ? (Array.isArray(spec.refLine) ? spec.refLine : [spec.refLine])
    : []
  const refMarkup = refLines.map((r, i) => (
    <ReferenceLine key={`ref-${i}`} y={r.value} stroke={resolveColor(r.color, 4)}
                   strokeDasharray="5 4" strokeWidth={1.5}
                   label={r.label
                     ? { value: r.label, position: 'insideTopRight', fontSize: 11,
                         fill: 'var(--text-tertiary)' }
                     : undefined} />
  ))

  const axes = (
    <>
      <CartesianGrid {...GRID_STYLE} vertical={false} />
      <XAxis dataKey="label" tick={AXIS_STYLE} tickLine={false} axisLine={false} dy={4} />
      <YAxis tick={AXIS_STYLE} tickLine={false} axisLine={false} width={40}
             tickFormatter={(v) => fmtCompact(Number(v))} />
      <Tooltip content={tip} cursor={{ fill: 'var(--surface)', radius: 6 }} />
    </>
  )

  if (spec.type === 'pie') {
    const valueKey = keys[0]
    const anyHi = spec.data.some(d => d.highlight === true)
    return (
      <PieChart>
        <Tooltip content={tip} />
        <Pie data={spec.data} dataKey={valueKey} nameKey="label" cx="50%" cy="50%"
             outerRadius={92} innerRadius={52} paddingAngle={3} cornerRadius={4}
             isAnimationActive={false}>
          {spec.data.map((d, i) => (
            <Cell key={i}
                  fill={typeof d.color === 'string' ? resolveColor(d.color, i) : color(i)}
                  fillOpacity={anyHi && d.highlight !== true ? 0.4 : 1}
                  stroke="var(--bg-elevated)" strokeWidth={2} />
          ))}
        </Pie>
      </PieChart>
    )
  }

  if (spec.type === 'line') {
    return (
      <LineChart data={spec.data} margin={{ top: 16, right: 12, left: 0, bottom: 0 }}>
        {axes}{refMarkup}
        {keys.map((k, i) => (
          <Line key={k} type="monotone" dataKey={k} stroke={seriesColor(i)} strokeWidth={2.5}
                dot={{ r: 3, fill: seriesColor(i), strokeWidth: 0 }}
                activeDot={{ r: 5 }} isAnimationActive={false} />
        ))}
      </LineChart>
    )
  }

  if (spec.type === 'area') {
    return (
      <AreaChart data={spec.data} margin={{ top: 16, right: 12, left: 0, bottom: 0 }}>
        <GradientDefs count={keys.length} kind="area" />
        {axes}{refMarkup}
        {keys.map((k, i) => (
          <Area key={k} type="monotone" dataKey={k} stroke={seriesColor(i)} strokeWidth={2.5}
                fill={spec.colors?.[i] ? seriesColor(i) : `url(#${gradId(i, 'area')})`}
                fillOpacity={spec.colors?.[i] ? 0.18 : 1} isAnimationActive={false} />
        ))}
      </AreaChart>
    )
  }

  // Bar. Single series → each bar its own color (gradient by default; a `color`
  // or `highlight` per row lets the agent emphasize one). Multiple series → one
  // color per series.
  const single = keys.length === 1
  const anyHi = spec.data.some(d => d.highlight === true)
  return (
    <BarChart data={spec.data} margin={{ top: 16, right: 12, left: 0, bottom: 0 }}>
      <GradientDefs count={single ? spec.data.length : keys.length} kind="bar" />
      {axes}{refMarkup}
      {single ? (
        <Bar dataKey={keys[0]} radius={[6, 6, 0, 0]} maxBarSize={56} isAnimationActive={false}>
          {spec.data.map((d, i) => {
            const explicit = typeof d.color === 'string' ? resolveColor(d.color, i) : null
            const fill = explicit
              ?? (anyHi && d.highlight === true ? CHART_COLORS.gold : `url(#${gradId(i, 'bar')})`)
            return <Cell key={i} fill={fill}
                         fillOpacity={anyHi && d.highlight !== true && !explicit ? 0.32 : 1} />
          })}
          {spec.data.length <= 7 && (
            <LabelList dataKey={keys[0]} position="top"
                       style={{ fill: 'var(--text-tertiary)', fontSize: 11, fontWeight: 600 }}
                       formatter={(v) => fmtCompact(Number(v ?? 0))} />
          )}
        </Bar>
      ) : keys.map((k, i) => (
        <Bar key={k} dataKey={k} radius={[5, 5, 0, 0]} maxBarSize={40} isAnimationActive={false}
             fill={spec.colors?.[i] ? seriesColor(i) : `url(#${gradId(i, 'bar')})`} />
      ))}
    </BarChart>
  )
}
