/**
 * Resolve a CSS color token to an `rgb(...)` string.
 *
 * The app's design tokens are `oklch(...)`. Some third-party renderers (Mermaid's
 * khroma engine, Babel-sandboxed artifacts, etc.) can't parse `oklch` — and
 * modern Chrome keeps `oklch` in computed style, so reading the var isn't enough.
 * Rasterizing the color on a 1×1 canvas and reading the pixel back always yields
 * sRGB regardless of the input color space, and still follows the active
 * (dark/light) theme because we read the live custom property.
 */
export function colorVarToRgb(name: string, fallback: string): string {
  if (typeof document === 'undefined') return fallback
  const raw = getComputedStyle(document.documentElement).getPropertyValue(name).trim()
  if (!raw) return fallback
  try {
    const canvas = document.createElement('canvas')
    canvas.width = canvas.height = 1
    const ctx = canvas.getContext('2d')
    if (!ctx) return fallback
    ctx.fillStyle = raw
    ctx.fillRect(0, 0, 1, 1)
    const [r, g, b] = ctx.getImageData(0, 0, 1, 1).data
    return `rgb(${r}, ${g}, ${b})`
  } catch {
    return fallback
  }
}

/** Read a CSS custom property verbatim (for non-color tokens like font-family). */
export function cssVar(name: string, fallback: string): string {
  if (typeof document === 'undefined') return fallback
  const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim()
  return value || fallback
}
