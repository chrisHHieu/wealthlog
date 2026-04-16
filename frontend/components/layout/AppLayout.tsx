'use client'

import { Sidebar } from './Sidebar'
import { Header } from './Header'
import { MobileNav } from './MobileNav'
import { FAB } from './FAB'
import { useAppStore } from '@/store/useAppStore'
import { cn } from '@/lib/utils'
import { TransactionDrawer } from '@/components/transactions/TransactionDrawer'
import { Suspense, useEffect } from 'react'

export function AppLayout({ children }: { children: React.ReactNode }) {
  const { sidebarCollapsed, openAddTransaction } = useAppStore()

  // Keyboard shortcuts
  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      const target = e.target as HTMLElement
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable) return

      if (e.key === 'n' || e.key === 'N') {
        e.preventDefault()
        openAddTransaction()
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [openAddTransaction])

  return (
    <div className="app-layout">
      <Sidebar />
      <Header />
      <main className={cn('main-content', sidebarCollapsed && 'sidebar-collapsed')}>
        <div className="page-container">
          {children}
        </div>
      </main>
      <FAB />
      <MobileNav />
      <Suspense><TransactionDrawer /></Suspense>
    </div>
  )
}
