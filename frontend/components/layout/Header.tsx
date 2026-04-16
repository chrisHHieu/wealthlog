'use client'

import { Plus, Menu } from 'lucide-react'
import { useAppStore } from '@/store/useAppStore'
import { getGreeting } from '@/lib/utils'
import { cn } from '@/lib/utils'
import { useQuery } from '@tanstack/react-query'
import { API_URL } from '@/lib/api'
import { usePathname } from 'next/navigation'

interface Settings {
  userName?: string
}

const PAGE_TITLES: Record<string, string> = {
  '/': 'Dashboard',
  '/transactions': 'Giao dịch',
  '/accounts': 'Tài khoản',
  '/budget': 'Ngân sách',
  '/recurring': 'Định kỳ',
  '/goals': 'Mục tiêu',
  '/investments': 'Đầu tư',
  '/reports': 'Báo cáo',
  '/settings': 'Cài đặt',
}

export function Header() {
  const { sidebarCollapsed, openAddTransaction, setMobileMenu, mobileMenuOpen } = useAppStore()
  const pathname = usePathname()

  const { data: settings } = useQuery<Settings>({
    queryKey: ['settings'],
    queryFn: () => fetch(`${API_URL}/api/settings`).then(r => r.json()).then(r => r.data ?? r),
  })

  const userName = settings?.userName ?? 'Bạn'
  const greeting = getGreeting()
  const now = new Date()
  const hour = now.getHours()
  const greetingIcon = hour < 5 ? '🌙' : hour < 11 ? '☀️' : hour < 14 ? '🌤️' : hour < 18 ? '🌤️' : '🌙'
  const pageTitle = PAGE_TITLES[pathname] || 'WealthLog'

  return (
    <header className={cn('header', sidebarCollapsed && 'sidebar-collapsed')}>
      {/* Mobile hamburger */}
      <button
        onClick={() => setMobileMenu(!mobileMenuOpen)}
        className="btn-icon"
        style={{ display: 'none', border: 'none', background: 'none' }}
        id="mobile-menu-btn"
      >
        <Menu size={20} />
      </button>

      {/* Left: Greeting + page context */}
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
          <span>{greetingIcon}</span>
        </div>
        <div style={{
          fontSize: 'var(--text-xs)',
          color: 'var(--text-tertiary)',
          marginTop: 2,
        }}>
          {pageTitle}
          {pathname === '/' && (
            <span> · {now.toLocaleDateString('vi-VN', { month: 'long', year: 'numeric' })}</span>
          )}
        </div>
      </div>

      {/* Right: Add transaction button */}
      <button
        id="header-add-transaction"
        onClick={() => openAddTransaction()}
        className="btn btn-primary btn-sm"
      >
        <Plus size={14} />
        <span className="header-btn-text">Thêm giao dịch</span>
      </button>

      <style jsx>{`
        @media (max-width: 1023px) {
          #mobile-menu-btn {
            display: flex !important;
          }
        }
        @media (max-width: 639px) {
          .header-btn-text {
            display: none;
          }
        }
      `}</style>
    </header>
  )
}
