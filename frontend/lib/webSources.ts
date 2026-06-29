import type { ChatStep } from '@/types/chat'

/** A citable web source parsed out of a web_search / web_extract tool result. */
export interface WebSource {
  url: string
  title: string
  domain: string
  date?: string
  /** Global citation number from web_search output; absent for extracted pages. */
  num?: number
}

const WEB_TOOL_NAMES = new Set(['web_search', 'web_extract'])
// "19. Title [2026-06-24]"  → num, title, optional trailing [date]
const RESULT_HEAD_RE = /^\s*(\d+)\.\s+(.*?)(?:\s+\[([^\]]+)\])?\s*$/
const EXTRACT_RE = /^Extracted from (\S+):/

export function domainOf(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, '')
  } catch {
    return url
  }
}

/** Favicon via Google's public service — no key, reliable across domains. */
export function faviconUrl(domain: string): string {
  return `https://www.google.com/s2/favicons?domain=${encodeURIComponent(domain)}&sz=64`
}

function isHttp(line: string): boolean {
  return /^https?:\/\//.test(line.trim())
}

/** Parse one web_search result block into ordered sources. */
function parseSearchResult(text: string): WebSource[] {
  const lines = text.split('\n')
  const out: WebSource[] = []
  for (let i = 0; i < lines.length; i++) {
    const head = RESULT_HEAD_RE.exec(lines[i])
    if (!head) continue
    // The URL is the next non-empty line; bail if the entry has no link.
    let j = i + 1
    while (j < lines.length && !lines[j].trim()) j++
    if (j >= lines.length || !isHttp(lines[j])) continue
    const url = lines[j].trim()
    out.push({
      url,
      title: head[2].trim() || domainOf(url),
      domain: domainOf(url),
      date: head[3],
      num: Number(head[1]),
    })
  }
  return out
}

/** Parse a web_extract result (single page) into one source. */
function parseExtractResult(text: string): WebSource[] {
  for (const line of text.split('\n')) {
    const m = EXTRACT_RE.exec(line.trim())
    if (m) return [{ url: m[1], title: domainOf(m[1]), domain: domainOf(m[1]) }]
  }
  return []
}

/**
 * Collect ordered, de-duplicated web sources across all web tool steps in a
 * message. Order = first appearance, which is the numbering inline [n] citations
 * map to (see linkifyCitations).
 */
export function collectWebSources(steps: ChatStep[] | undefined): WebSource[] {
  if (!steps) return []
  const seen = new Set<string>()
  const out: WebSource[] = []
  for (const step of steps) {
    if (step.kind !== 'tool' || !WEB_TOOL_NAMES.has(step.name) || !step.result) continue
    const parsed = step.name === 'web_extract'
      ? parseExtractResult(step.result)
      : parseSearchResult(step.result)
    for (const src of parsed) {
      if (seen.has(src.url)) continue
      seen.add(src.url)
      out.push(src)
    }
  }
  return out
}

/** Map a source's global citation number → the source (first wins on dupes). */
function citationMap(sources: WebSource[]): Map<number, WebSource> {
  const map = new Map<number, WebSource>()
  for (const s of sources) {
    if (s.num !== undefined && !map.has(s.num)) map.set(s.num, s)
  }
  return map
}

/**
 * Turn bare ``[n]`` citation markers into markdown links to the source whose
 * GLOBAL number is n (web_search results are renumbered 1..N across the whole
 * turn by the runner, so n is unambiguous). Chips show the source title on hover.
 *
 * Robustness across providers: a marker that doesn't map to a real source — a
 * model hallucinating "[23]" when only 6 sources exist, common with weaker
 * models — is STRIPPED (along with its leading space) rather than left dangling.
 * The Sources footer stays authoritative. Only runs when the message has web
 * sources, so normal bracketed text is safe.
 */
// A fenced code block — ```...```  — including an unclosed trailing fence while
// streaming. Citation rewriting must NEVER touch what's inside: `[n]` there is
// code (e.g. an array index `arr[1]` in an artifact/visual), not a citation, and
// linkifying it produces broken syntax.
const FENCE_RE = /```[\s\S]*?(?:```|$)/g

export function linkifyCitations(content: string, sources: WebSource[]): string {
  if (sources.length === 0) return content
  const map = citationMap(sources)
  const linkify = (text: string) =>
    text.replace(/(\s*)\[(\d+)\]/g, (_m, space: string, num: string) => {
      const src = map.get(Number(num))
      if (!src) return ''
      const title = src.title.replace(/["\n]/g, " ").slice(0, 80)
      return `${space}[${num}](${src.url} "${title}")`
    })
  // Split on fenced blocks (captured), linkify only the prose between them.
  return content
    .split(new RegExp(`(${FENCE_RE.source})`, "g"))
    .map((part, i) => (i % 2 === 0 ? linkify(part) : part))
    .join("")
}

// When the model cites nothing usable (e.g. a weaker model that confabulated all
// its numbers), fall back to showing this many top sources rather than an empty
// or 30-card footer.
const FOOTER_FALLBACK_CAP = 8

/**
 * The sources to show in the answer's "Sources" footer. If the answer cites real
 * sources, show ONLY those (so the footer matches the inline [n] chips instead of
 * dumping every raw search hit). Extracted pages (no number) are always kept —
 * the user asked to read them. If nothing maps, fall back to the top sources.
 */
export function citedFooterSources(content: string, sources: WebSource[]): WebSource[] {
  if (sources.length === 0) return sources
  const map = citationMap(sources)
  const cited = new Set<number>()
  // Ignore `[n]` inside fenced code (array indices etc.) — only real prose cites.
  const prose = content.replace(FENCE_RE, "")
  for (const m of prose.matchAll(/\[(\d+)\]/g)) {
    const n = Number(m[1])
    if (map.has(n)) cited.add(n)
  }
  if (cited.size === 0) return sources.slice(0, FOOTER_FALLBACK_CAP)
  return sources.filter(s => s.num === undefined || cited.has(s.num))
}
