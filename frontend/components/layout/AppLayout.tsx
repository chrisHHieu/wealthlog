'use client'

import { Sidebar } from './Sidebar'
import { Header } from './Header'
import { MobileNav } from './MobileNav'
import { useAppStore } from '@/store/useAppStore'
import { cn } from '@/lib/utils'
import { TransactionDrawer } from '@/components/transactions/TransactionDrawer'
import { CommandPalette } from '@/components/ui/CommandPalette'
import { Suspense, useEffect } from 'react'

export function AppLayout({ children }: { children: React.ReactNode }) {
  const { sidebarCollapsed, openAddTransaction, toggleCommandPalette } = useAppStore()

  // Keyboard shortcuts (chat moved to the Chip app)
  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        toggleCommandPalette()
        return
      }
      const target = e.target as HTMLElement
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable) return
      if (e.key === 'n' || e.key === 'N') {
        e.preventDefault()
        openAddTransaction()
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [openAddTransaction, toggleCommandPalette])

  return (
    <div className="app-layout">
      <Sidebar />
      <Header />
      <main className={cn('main-content', sidebarCollapsed && 'sidebar-collapsed')}>
        <div className="page-container">
          {children}
        </div>
      </main>
      <MobileNav />
      <CommandPalette />
      <Suspense><TransactionDrawer /></Suspense>
    </div>
  )
}
