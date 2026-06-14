'use client'

import { useEffect } from 'react'
import { useAppStore } from '@/store/useAppStore'

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const theme = useAppStore(s => s.theme)

  useEffect(() => {
    const root = document.documentElement
    if (root.getAttribute('data-theme') === theme) return

    const apply = () => root.setAttribute('data-theme', theme)

    // Crossfade the whole page on theme switch when the browser supports it
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    const startViewTransition = (
      document as Document & { startViewTransition?: (cb: () => void) => void }
    ).startViewTransition?.bind(document)

    if (!reduced && startViewTransition && root.hasAttribute('data-theme')) {
      startViewTransition(apply)
    } else {
      apply()
    }
  }, [theme])

  return <>{children}</>
}
