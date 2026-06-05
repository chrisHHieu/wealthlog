'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { AnimatePresence, motion } from 'framer-motion'
import {
  ArrowLeftRight,
  BarChart2,
  ChevronLeft,
  ChevronRight,
  LayoutDashboard,
  Moon,
  PiggyBank,
  Repeat,
  Settings,
  Sparkles,
  Sun,
  Target,
  TrendingUp,
  Wallet,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useAppStore } from '@/store/useAppStore'

const NAV_ITEMS = [
  { href: '/', icon: LayoutDashboard, label: 'Dashboard', color: 'var(--accent-green)' },
  { href: '/transactions', icon: ArrowLeftRight, label: 'Transactions', color: 'var(--accent-blue)' },
  { href: '/accounts', icon: Wallet, label: 'Accounts', color: 'var(--accent-gold)' },
  { href: '/budget', icon: PiggyBank, label: 'Budget', color: 'var(--accent-amber)' },
  { href: '/recurring', icon: Repeat, label: 'Recurring', color: 'var(--accent-purple)' },
  { href: '/goals', icon: Target, label: 'Goals', color: 'var(--accent-green)' },
  { href: '/investments', icon: TrendingUp, label: 'Investments', color: 'var(--accent-gold)' },
  { href: '/reports', icon: BarChart2, label: 'Reports', color: 'var(--accent-blue)' },
  { href: '/chat', icon: Sparkles, label: 'Chip Assistant', color: 'var(--accent-purple)' },
]

export function Sidebar() {
  const pathname = usePathname()
  const { sidebarCollapsed, mobileMenuOpen, toggleSidebar, setMobileMenu, theme, toggleTheme } = useAppStore()

  const handleNavClick = () => {
    if (mobileMenuOpen) setMobileMenu(false)
  }

  return (
    <>
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

      <aside className={cn('sidebar', sidebarCollapsed && 'collapsed', mobileMenuOpen && 'mobile-open')}>
        <div className="sidebar-logo">
          <div className="sidebar-logo-icon">W</div>
          <AnimatePresence>
            {!sidebarCollapsed && (
              <motion.span
                className="sidebar-logo-text"
                initial={{ opacity: 0, x: -4 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -4 }}
                transition={{ duration: 0.2 }}
              >
                WealthLog
              </motion.span>
            )}
          </AnimatePresence>
        </div>

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
                        className="sidebar-label"
                        initial={{ opacity: 0, x: -4 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0, x: -4 }}
                        transition={{ duration: 0.2 }}
                        style={{
                          fontSize: 'var(--text-sm)',
                          fontWeight: isActive ? 600 : 500,
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

        <div style={{ padding: 'var(--space-2) var(--space-2) var(--space-4)', borderTop: '1px solid var(--surface-border)' }}>
          <Link
            href="/settings"
            className={cn('sidebar-item', pathname === '/settings' && 'active')}
            data-tooltip={sidebarCollapsed ? 'Settings' : undefined}
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
                  className="sidebar-label"
                  initial={{ opacity: 0, x: -4 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -4 }}
                  transition={{ duration: 0.2 }}
                  style={{ fontSize: 'var(--text-sm)', fontWeight: 500 }}
                >
                  Settings
                </motion.span>
              )}
            </AnimatePresence>
          </Link>

          <button
            onClick={toggleTheme}
            className="sidebar-item"
            data-tooltip={sidebarCollapsed ? (theme === 'dark' ? 'Light mode' : 'Dark mode') : undefined}
            style={{ width: '100%', cursor: 'pointer', background: 'none', border: 'none' }}
          >
            <div className="sidebar-icon">
              {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
            </div>
            <AnimatePresence>
              {!sidebarCollapsed && (
                <motion.span
                  className="sidebar-label"
                  initial={{ opacity: 0, x: -4 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -4 }}
                  transition={{ duration: 0.2 }}
                  style={{ fontSize: 'var(--text-sm)', fontWeight: 500 }}
                >
                  {theme === 'dark' ? 'Light mode' : 'Dark mode'}
                </motion.span>
              )}
            </AnimatePresence>
          </button>

          <button
            onClick={toggleSidebar}
            className="sidebar-item"
            data-tooltip={sidebarCollapsed ? 'Expand' : undefined}
            style={{ width: '100%', cursor: 'pointer', background: 'none', border: 'none', marginTop: 4 }}
          >
            <div className="sidebar-icon">
              {sidebarCollapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
            </div>
            <AnimatePresence>
              {!sidebarCollapsed && (
                <motion.span
                  className="sidebar-label"
                  initial={{ opacity: 0, x: -4 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -4 }}
                  transition={{ duration: 0.2 }}
                  style={{ fontSize: 'var(--text-sm)', fontWeight: 500 }}
                >
                  Collapse
                </motion.span>
              )}
            </AnimatePresence>
          </button>
        </div>
      </aside>
    </>
  )
}
