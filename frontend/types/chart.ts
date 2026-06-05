export interface ChartTooltipPayload<T = Record<string, unknown>> {
  dataKey?: string | number
  name?: string
  value?: number | string
  color?: string
  payload?: T
}

export interface ChartTooltipProps<T = Record<string, unknown>> {
  active?: boolean
  payload?: ChartTooltipPayload<T>[]
  label?: string
}
