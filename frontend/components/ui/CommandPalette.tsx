'use client'

import { useEffect, useMemo, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useQuery } from '@tanstack/react-query'
import {
  ArrowLeftRight,
  BarChart2,
  LayoutDashboard,
  Moon,
  PiggyBank,
  Plus,
  Repeat,
  Search,
  Settings,
  Sparkles,
  Sun,
  Target,
  TrendingUp,
  Wallet,
} from 'lucide-react'
import { Portal } from '@/components/ui/Portal'
import { apiGet, queryKeys } from '@/lib/api'
import { fuzzyRank } from '@/lib/fuzzy'
import { formatVNDCompact } from '@/lib/utils'
import { useAppStore } from '@/store/useAppStore'
import type { Goal, PaginatedResponse, Transaction } from '@/types'

const PAGES = [
  { href: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { href: '/transactions', icon: ArrowLeftRight, label: 'Transactions' },
  { href: '/accounts', icon: Wallet, label: 'Accounts' },
  { href: '/budget', icon: PiggyBank, label: 'Budget' },
  { href: '/recurring', icon: Repeat, label: 'Recurring' },
  { href: '/goals', icon: Target, label: 'Goals' },
  { href: '/investments', icon: TrendingUp, label: 'Investments' },
  { href: '/reports', icon: BarChart2, label: 'Reports' },
  { href: '/chat', icon: Sparkles, label: 'Chip Assistant' },
  { href: '/settings', icon: Settings, label: 'Settings' },
]

const MAX_PER_GROUP = 5

interface Account {
  id: string
  name: string
  icon: string
  balance: number
  isActive: boolean
}

interface PaletteItem {
  id: string
  group: string
  label: string
  hint?: string
  icon: React.ReactNode
  run: () => void
}

export function CommandPalette() {
  const router = useRouter()
  const {
    commandPaletteOpen,
    setCommandPalette,
    openAddTransaction,
    openEditTransaction,
    openChat,
    toggleTheme,
    theme,
  } = useAppStore()

  const [query, setQuery] = useState('')
  const [debouncedQuery, setDebouncedQuery] = useState('')
  const [selectedIndex, setSelectedIndex] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)
  const listRef = useRef<HTMLDivElement>(null)

  // Reset on open
  useEffect(() => {
    if (commandPaletteOpen) {
      setQuery('')
      setDebouncedQuery('')
      setSelectedIndex(0)
    }
  }, [commandPaletteOpen])

  useEffect(() => {
    const t = setTimeout(() => setDebouncedQuery(query.trim()), 200)
    return () => clearTimeout(t)
  }, [query])

  const { data: txResults } = useQuery<PaginatedResponse<Transaction>>({
    queryKey: ['cmd-tx-search', debouncedQuery],
    queryFn: () =>
      apiGet<PaginatedResponse<Transaction>>('/api/transactions', {
        search: debouncedQuery,
        page: 1,
        pageSize: MAX_PER_GROUP,
      }),
    enabled: commandPaletteOpen && debouncedQuery.length >= 2,
    staleTime: 10_000,
  })

  const { data: accounts = [] } = useQuery<Account[]>({
    queryKey: queryKeys.accounts,
    queryFn: () => apiGet<Account[]>('/api/accounts'),
    enabled: commandPaletteOpen,
    staleTime: 60_000,
  })

  const { data: goals = [] } = useQuery<Goal[]>({
    queryKey: queryKeys.goals,
    queryFn: () => apiGet<Goal[]>('/api/goals'),
    enabled: commandPaletteOpen,
    staleTime: 60_000,
  })

  function close() {
    setCommandPalette(false)
  }

  const items = useMemo<PaletteItem[]>(() => {
    const q = query.trim()

    const pageItems: PaletteItem[] = fuzzyRank(PAGES, q, p => p.label).map(p => ({
      id: `page-${p.href}`,
      group: 'Pages',
      label: p.label,
      hint: 'Go to',
      icon: <p.icon size={15} />,
      run: () => router.push(p.href),
    }))

    const actionDefs = [
      {
        id: 'action-add-expense',
        label: 'Add expense',
        icon: <Plus size={15} />,
        run: () => openAddTransaction('expense'),
      },
      {
        id: 'action-add-income',
        label: 'Add income',
        icon: <Plus size={15} />,
        run: () => openAddTransaction('income'),
      },
      {
        id: 'action-ask-ai',
        label: 'Ask AI assistant',
        hint: 'Ctrl /',
        icon: <Sparkles size={15} />,
        run: () => openChat(),
      },
      {
        id: 'action-toggle-theme',
        label: theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode',
        icon: theme === 'dark' ? <Sun size={15} /> : <Moon size={15} />,
        run: () => toggleTheme(),
      },
    ]
    const actionItems: PaletteItem[] = fuzzyRank(actionDefs, q, a => a.label).map(a => ({
      ...a,
      group: 'Actions',
    }))

    // Entity groups only show up once the user starts typing
    const accountItems: PaletteItem[] = !q
      ? []
      : fuzzyRank(accounts.filter(a => a.isActive), q, a => a.name)
          .slice(0, MAX_PER_GROUP)
          .map(a => ({
            id: `account-${a.id}`,
            group: 'Accounts',
            label: a.name,
            hint: formatVNDCompact(a.balance),
            icon: <span style={{ fontSize: 14 }}>{a.icon || '🏦'}</span>,
            run: () => router.push(`/transactions?accountId=${a.id}`),
          }))

    const goalItems: PaletteItem[] = !q
      ? []
      : fuzzyRank(goals, q, g => g.name)
          .slice(0, MAX_PER_GROUP)
          .map(g => {
            const pct = g.targetAmount > 0
              ? Math.min(100, Math.round((g.currentAmount / g.targetAmount) * 100))
              : 0
            return {
              id: `goal-${g.id}`,
              group: 'Goals',
              label: g.name,
              hint: `${pct}% of ${formatVNDCompact(g.targetAmount)}`,
              icon: <span style={{ fontSize: 14 }}>{g.icon || '🎯'}</span>,
              run: () => router.push('/goals'),
            }
          })

    const txItems: PaletteItem[] = (debouncedQuery.length >= 2 ? txResults?.data ?? [] : []).map(t => ({
      id: `tx-${t.id}`,
      group: 'Transactions',
      label: t.description || t.categoryName || 'Transaction',
      hint: `${t.type === 'expense' ? '-' : '+'}${formatVNDCompact(t.amount)} · ${new Date(t.date).toLocaleDateString('en-US', { day: 'numeric', month: 'short' })}`,
      icon: <span style={{ fontSize: 14 }}>{t.categoryIcon || '💸'}</span>,
      run: () => openEditTransaction(t.id),
    }))

    return [...pageItems, ...actionItems, ...accountItems, ...goalItems, ...txItems]
  }, [query, debouncedQuery, txResults, accounts, goals, theme, router, openAddTransaction, openChat, toggleTheme, openEditTransaction])

  // Clamp selection when the list shrinks
  useEffect(() => {
    setSelectedIndex(i => Math.min(i, Math.max(items.length - 1, 0)))
  }, [items.length])

  useEffect(() => {
    listRef.current
      ?.querySelector('[data-selected="true"]')
      ?.scrollIntoView({ block: 'nearest' })
  }, [selectedIndex])

  function onKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setSelectedIndex(i => Math.min(i + 1, items.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setSelectedIndex(i => Math.max(i - 1, 0))
    } else if (e.key === 'Enter') {
      e.preventDefault()
      const item = items[selectedIndex]
      if (item) {
        close()
        item.run()
      }
    } else if (e.key === 'Escape') {
      e.preventDefault()
      close()
    }
  }

  if (!commandPaletteOpen) return null

  const groups = Array.from(new Set(items.map(i => i.group)))

  return (
    <Portal>
      <div className="overlay" onClick={close} />
      <div className="cmd-palette" role="dialog" aria-label="Command palette">
        <div className="cmd-input-row">
          <Search size={16} />
          <input
            ref={inputRef}
            autoFocus
            className="cmd-input"
            placeholder="Search pages, accounts, goals, transactions…"
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={onKeyDown}
          />
          <kbd>Esc</kbd>
        </div>

        <div className="cmd-list" ref={listRef}>
          {items.length === 0 && (
            <div className="cmd-empty">No results for &ldquo;{query}&rdquo;</div>
          )}
          {groups.map(group => (
            <div key={group}>
              <div className="cmd-section-label">{group}</div>
              {items.map((item, index) =>
                item.group === group ? (
                  <button
                    key={item.id}
                    className="cmd-item"
                    data-selected={index === selectedIndex}
                    onMouseEnter={() => setSelectedIndex(index)}
                    onClick={() => {
                      close()
                      item.run()
                    }}
                  >
                    <span className="cmd-item-icon">{item.icon}</span>
                    <span className="cmd-item-label">{item.label}</span>
                    {item.hint && <span className="cmd-item-hint">{item.hint}</span>}
                  </button>
                ) : null,
              )}
            </div>
          ))}
        </div>
      </div>
    </Portal>
  )
}
