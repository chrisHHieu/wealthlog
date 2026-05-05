'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { motion, AnimatePresence } from 'framer-motion'
import {
  LayoutDashboard,
  ArrowLeftRight,
  Wallet,
  PiggyBank,
  Target,
  TrendingUp,
  BarChart2,
  Settings,
  Sun,
  Moon,
  ChevronLeft,
  ChevronRight,
  Repeat,
  Sparkles,
} from 'lucide-react'
import { useAppStore } from '@/store/useAppStore'
import { cn } from '@/lib/utils'

const NAV_ITEMS = [
  { href: '/', icon: LayoutDashboard, label: 'Dashboard', color: 'var(--accent-green)' },
  { href: '/transactions', icon: ArrowLeftRight, label: 'Giao dịch', color: 'var(--accent-blue)' },
  { href: '/accounts', icon: Wallet, label: 'Tài khoản', color: 'var(--accent-gold)' },
  { href: '/budget', icon: PiggyBank, label: 'Ngân sách', color: 'var(--accent-amber)' },
  { href: '/recurring', icon: Repeat, label: 'Định kỳ', color: 'var(--accent-purple)' },
  { href: '/goals', icon: Target, label: 'Mục tiêu', color: 'var(--accent-green)' },
  { href: '/investments', icon: TrendingUp, label: 'Đầu tư', color: 'var(--accent-gold)' },
  { href: '/reports', icon: BarChart2, label: 'Báo cáo', color: 'var(--accent-blue)' },
  { href: '/chat', icon: Sparkles, label: 'Trợ Lý Chip', color: 'var(--accent-purple)' },
]

export function Sidebar() {
  const pathname = usePathname()
  const { sidebarCollapsed, mobileMenuOpen, toggleSidebar, setMobileMenu, theme, toggleTheme } = useAppStore()

  const handleNavClick = () => {
    if (mobileMenuOpen) setMobileMenu(false)
  }

  return (
    <>
      {/* Mobile overlay */}
      <AnimatePresence>
        {mobileMenuOpen && (
          <motion.div
            className="sidebar-overlay"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            onClick={() => setMobileMenu(false)}
          />
        )}
      </AnimatePresence>

      <aside className={cn(
        'sidebar',
        sidebarCollapsed && 'collapsed',
        mobileMenuOpen && 'mobile-open'
      )}>
        {/* Logo */}
        <div className="sidebar-logo">
          <div className="sidebar-logo-icon">W</div>
          <AnimatePresence>
            {!sidebarCollapsed && (
              <motion.span
                className="sidebar-logo-text"
                initial={{ opacity: 0, width: 0 }}
                animate={{ opacity: 1, width: 'auto' }}
                exit={{ opacity: 0, width: 0 }}
                transition={{ duration: 0.2 }}
              >
                WealthLog
              </motion.span>
            )}
          </AnimatePresence>
        </div>

        {/* Navigation */}
        <nav style={{ flex: 1, padding: 'var(--space-3) var(--space-2)', overflowY: 'auto' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            {NAV_ITEMS.map((item) => {
              const isActive = item.href === '/'
                ? pathname === '/'
                : pathname.startsWith(item.href)

              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn('sidebar-item', isActive && 'active')}
                  data-tooltip={sidebarCollapsed ? item.label : undefined}
                  onClick={handleNavClick}
                >
                  {/* Animated active pill indicator */}
                  {isActive && (
                    <motion.div
                      className="sidebar-active-pill"
                      layoutId="sidebar-active-pill"
                      transition={{ type: 'spring', stiffness: 350, damping: 30 }}
                    />
                  )}
                  <div
                    className="sidebar-icon"
                    style={isActive ? { background: `${item.color}12`, color: item.color } : undefined}
                  >
                    <item.icon size={18} />
                  </div>
                  <AnimatePresence>
                    {!sidebarCollapsed && (
                      <motion.span
                        initial={{ opacity: 0, width: 0 }}
                        animate={{ opacity: 1, width: 'auto' }}
                        exit={{ opacity: 0, width: 0 }}
                        transition={{ duration: 0.2 }}
                        style={{
                          fontSize: 'var(--text-sm)',
                          fontWeight: isActive ? 600 : 500,
                          overflow: 'hidden',
                          whiteSpace: 'nowrap',
                        }}
                      >
                        {item.label}
                      </motion.span>
                    )}
                  </AnimatePresence>
                </Link>
              )
            })}
          </div>
        </nav>

        {/* Bottom actions */}
        <div style={{ padding: 'var(--space-2) var(--space-2) var(--space-4)', borderTop: '1px solid var(--surface-border)' }}>
          <Link
            href="/settings"
            className={cn('sidebar-item', pathname === '/settings' && 'active')}
            data-tooltip={sidebarCollapsed ? 'Cài đặt' : undefined}
            onClick={handleNavClick}
          >
            {pathname === '/settings' && (
              <motion.div
                className="sidebar-active-pill"
                layoutId="sidebar-active-pill"
                transition={{ type: 'spring', stiffness: 350, damping: 30 }}
              />
            )}
            <div className="sidebar-icon">
              <Settings size={18} />
            </div>
            <AnimatePresence>
              {!sidebarCollapsed && (
                <motion.span
                  initial={{ opacity: 0, width: 0 }}
                  animate={{ opacity: 1, width: 'auto' }}
                  exit={{ opacity: 0, width: 0 }}
                  transition={{ duration: 0.2 }}
                  style={{ fontSize: 'var(--text-sm)', fontWeight: 500, overflow: 'hidden', whiteSpace: 'nowrap' }}
                >
                  Cài đặt
                </motion.span>
              )}
            </AnimatePresence>
          </Link>

          <button
            onClick={toggleTheme}
            className="sidebar-item"
            data-tooltip={sidebarCollapsed ? (theme === 'dark' ? 'Chế độ sáng' : 'Chế độ tối') : undefined}
            style={{ width: '100%', cursor: 'pointer', background: 'none', border: 'none' }}
          >
            <div className="sidebar-icon">
              {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
            </div>
            <AnimatePresence>
              {!sidebarCollapsed && (
                <motion.span
                  initial={{ opacity: 0, width: 0 }}
                  animate={{ opacity: 1, width: 'auto' }}
                  exit={{ opacity: 0, width: 0 }}
                  transition={{ duration: 0.2 }}
                  style={{ fontSize: 'var(--text-sm)', fontWeight: 500, overflow: 'hidden', whiteSpace: 'nowrap' }}
                >
                  {theme === 'dark' ? 'Chế độ sáng' : 'Chế độ tối'}
                </motion.span>
              )}
            </AnimatePresence>
          </button>

          {/* Collapse toggle */}
          <button
            onClick={toggleSidebar}
            className="sidebar-item"
            data-tooltip={sidebarCollapsed ? 'Mở rộng' : undefined}
            style={{ width: '100%', cursor: 'pointer', background: 'none', border: 'none', marginTop: 4 }}
          >
            <div className="sidebar-icon">
              {sidebarCollapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
            </div>
            <AnimatePresence>
              {!sidebarCollapsed && (
                <motion.span
                  initial={{ opacity: 0, width: 0 }}
                  animate={{ opacity: 1, width: 'auto' }}
                  exit={{ opacity: 0, width: 0 }}
                  transition={{ duration: 0.2 }}
                  style={{ fontSize: 'var(--text-sm)', fontWeight: 500, overflow: 'hidden', whiteSpace: 'nowrap' }}
                >
                  Thu gọn
                </motion.span>
              )}
            </AnimatePresence>
          </button>
        </div>
      </aside>
    </>
  )
}
