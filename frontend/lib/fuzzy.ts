/**
 * Lightweight fuzzy matcher: case-insensitive subsequence with a quality score.
 * Returns 0 when the query is not a subsequence of the text; higher is better.
 * Scoring favors word-start hits and consecutive runs, then shorter targets.
 */
export function fuzzyScore(query: string, text: string): number {
  const q = query.toLowerCase()
  const t = text.toLowerCase()
  if (!q) return 1

  let score = 0
  let ti = 0
  let prevMatch = -2

  for (const ch of q) {
    let found = -1
    for (; ti < t.length; ti++) {
      if (t[ti] === ch) {
        found = ti
        break
      }
    }
    if (found === -1) return 0

    score += 1
    if (found === 0 || t[found - 1] === ' ' || t[found - 1] === '-') score += 3
    if (found === prevMatch + 1) score += 2
    prevMatch = found
    ti = found + 1
  }

  return score + Math.max(0, 20 - t.length) * 0.05
}

/** Rank items by fuzzy score against a query; empty query keeps original order. */
export function fuzzyRank<T>(items: T[], query: string, label: (item: T) => string): T[] {
  if (!query) return items
  return items
    .map(item => ({ item, score: fuzzyScore(query, label(item)) }))
    .filter(r => r.score > 0)
    .sort((a, b) => b.score - a.score)
    .map(r => r.item)
}
