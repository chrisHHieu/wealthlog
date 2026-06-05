import { ChevronLeft, ChevronRight } from 'lucide-react'

interface PaginationProps {
  page: number
  totalPages: number
  setPage: (p: number | ((prev: number) => number)) => void
}

export function Pagination({ page, totalPages, setPage }: PaginationProps) {
  if (totalPages <= 1) return null

  return (
    <div style={{
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      gap: 8, marginTop: 24, paddingBottom: 8,
    }}>
      <button
        className="btn btn-secondary btn-sm"
        onClick={() => setPage(p => Math.max(1, p - 1))}
        disabled={page === 1}
        style={{ display: 'flex', alignItems: 'center', gap: 4 }}
      >
        <ChevronLeft size={15} /> Previous
      </button>

      <div style={{ display: 'flex', gap: 4 }}>
        {Array.from({ length: totalPages }, (_, i) => i + 1)
          .filter(p => p === 1 || p === totalPages || Math.abs(p - page) <= 1)
          .reduce<(number | '...')[]>((acc, p, i, arr) => {
            if (i > 0 && p - (arr[i - 1] as number) > 1) acc.push('...')
            acc.push(p)
            return acc
          }, [])
          .map((p, i) =>
            p === '...' ? (
              <span key={`ellipsis-${i}`} style={{ padding: '0 4px', color: 'var(--text-tertiary)', lineHeight: '32px' }}>…</span>
            ) : (
              <button
                key={p}
                onClick={() => setPage(p as number)}
                className="btn btn-sm"
                style={{
                  minWidth: 32,
                  ...(page === p
                    ? { background: 'var(--accent-green)', color: '#0f0f14', border: 'none' }
                    : { background: 'var(--surface)', color: 'var(--text-secondary)', border: '1px solid var(--surface-border)' })
                }}
              >
                {p}
              </button>
            )
          )}
      </div>

      <button
        className="btn btn-secondary btn-sm"
        onClick={() => setPage(p => Math.min(totalPages, p + 1))}
        disabled={page === totalPages}
        style={{ display: 'flex', alignItems: 'center', gap: 4 }}
      >
        Sau <ChevronRight size={15} />
      </button>
    </div>
  )
}
