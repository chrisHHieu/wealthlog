'use client'

import { Menu, Moon, Plus, Sparkles, Sun } from 'lucide-react'
import { usePathname } from 'next/navigation'
import { useQuery } from '@tanstack/react-query'
import { apiGet, queryKeys } from '@/lib/api'
import { cn, getGreeting } from '@/lib/utils'
import { useAppStore } from '@/store/useAppStore'

interface Settings {
  userName?: string
}

interface SettingsResponse {
  data?: Settings
}

const PAGE_TITLES: Record<string, string> = {
  '/': 'Dashboard',
  '/transactions': 'Transactions',
  '/accounts': 'Accounts',
  '/budget': 'Budget',
  '/recurring': 'Recurring',
  '/goals': 'Goals',
  '/investments': 'Investments',
  '/reports': 'Reports',
  '/settings': 'Settings',
  '/chat': 'Chip Assistant',
}

export function Header() {
  const { sidebarCollapsed, openAddTransaction, setMobileMenu, mobileMenuOpen, chatOpen, toggleChat } = useAppStore()
  const pathname = usePathname()

  const { data: settings } = useQuery<Settings>({
    queryKey: queryKeys.settings,
    queryFn: async () => {
      const response = await apiGet<Settings | SettingsResponse>('/api/settings')
      if ('data' in response && response.data) return response.data
      return response as Settings
    },
  })

  const userName = settings?.userName ?? 'You'
  const greeting = getGreeting()
  const now = new Date()
  const isDaytime = now.getHours() >= 5 && now.getHours() < 18
  const pageTitle = PAGE_TITLES[pathname] || 'WealthLog'

  return (
    <header className={cn('header', sidebarCollapsed && 'sidebar-collapsed', chatOpen && 'chat-open')}>
      <button
        onClick={() => setMobileMenu(!mobileMenuOpen)}
        className="btn-icon"
        style={{ display: 'none', border: 'none', background: 'none' }}
        id="mobile-menu-btn"
        aria-label="Open navigation"
      >
        <Menu size={20} />
      </button>

      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{
          fontSize: 'var(--text-base)',
          fontWeight: 600,
          color: 'var(--text-primary)',
          display: 'flex',
          alignItems: 'center',
          gap: 'var(--space-2)',
        }}>
          <span>{greeting}, {userName}</span>
          {isDaytime ? <Sun size={16} /> : <Moon size={16} />}
        </div>
        <div style={{
          fontSize: 'var(--text-xs)',
          color: 'var(--text-tertiary)',
          marginTop: 2,
        }}>
          {pageTitle}
          {pathname === '/' && (
            <span> - {now.toLocaleDateString('en-US', { month: 'long', year: 'numeric' })}</span>
          )}
        </div>
      </div>

      <div className="header-actions">
        <button
          id="header-add-transaction"
          onClick={() => openAddTransaction()}
          className="btn btn-primary btn-sm"
        >
          <Plus size={14} />
          <span className="header-btn-text">Add transaction</span>
        </button>

        {!chatOpen && pathname !== '/chat' && (
          <button
            onClick={toggleChat}
            className="chat-toggle-header"
            title="AI assistant (Ctrl+/)"
          >
            <Sparkles size={15} />
            <span className="header-btn-text">AI</span>
          </button>
        )}
      </div>

      <style jsx>{`
        .header-actions {
          display: flex;
          align-items: center;
          gap: var(--space-2);
          flex-shrink: 0;
        }

        @media (max-width: 1023px) {
          #mobile-menu-btn {
            display: flex !important;
          }
        }
        @media (max-width: 639px) {
          .header-actions {
            gap: var(--space-1);
          }

          #header-add-transaction {
            display: none;
          }

          .header-btn-text {
            display: none;
          }

          .header-actions :global(.btn),
          .header-actions :global(.chat-toggle-header) {
            width: 40px;
            height: 40px;
            padding: 0;
            justify-content: center;
            flex: 0 0 auto;
          }
        }
      `}</style>
    </header>
  )
}
