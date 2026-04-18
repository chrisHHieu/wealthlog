'use client'

import { Sidebar } from './Sidebar'
import { Header } from './Header'
import { MobileNav } from './MobileNav'
import { useAppStore } from '@/store/useAppStore'
import { cn } from '@/lib/utils'
import { TransactionDrawer } from '@/components/transactions/TransactionDrawer'
import { ChatPanel } from '@/components/chat/ChatPanel'
import { Suspense, useEffect } from 'react'

export function AppLayout({ children }: { children: React.ReactNode }) {
  const { sidebarCollapsed, chatOpen, openAddTransaction, toggleChat } = useAppStore()

  // Keyboard shortcuts
  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      const target = e.target as HTMLElement
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable) return

      if (e.key === 'n' || e.key === 'N') {
        e.preventDefault()
        openAddTransaction()
      }
      if (e.key === '/' && e.ctrlKey) {
        e.preventDefault()
        toggleChat()
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [openAddTransaction, toggleChat])

  return (
    <div className="app-layout">
      <Sidebar />
      <Header />
      <main className={cn('main-content', sidebarCollapsed && 'sidebar-collapsed', chatOpen && 'chat-open')}>
        <div className="page-container">
          {children}
        </div>
      </main>
      <MobileNav />
      <ChatPanel />
      <Suspense><TransactionDrawer /></Suspense>
    </div>
  )
}
