'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  LayoutDashboard,
  ArrowLeftRight,
  Wallet,
  PiggyBank,
  MoreHorizontal,
} from 'lucide-react'
import { cn } from '@/lib/utils'

const MOBILE_NAV_ITEMS = [
  { href: '/', icon: LayoutDashboard, label: 'Tổng quan' },
  { href: '/transactions', icon: ArrowLeftRight, label: 'Giao dịch' },
  { href: '/accounts', icon: Wallet, label: 'Tài khoản' },
  { href: '/budget', icon: PiggyBank, label: 'Ngân sách' },
]

export function MobileNav() {
  const pathname = usePathname()

  return (
    <div className="mobile-nav">
      <div className="mobile-nav-inner">
        {MOBILE_NAV_ITEMS.map((item) => {
          const isActive = item.href === '/'
            ? pathname === '/'
            : pathname.startsWith(item.href)

          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn('mobile-nav-item', isActive && 'active')}
            >
              <item.icon size={20} strokeWidth={isActive ? 2.5 : 2} />
              <span>{item.label}</span>
            </Link>
          )
        })}
      </div>
    </div>
  )
}
