'use client'

import { useState, useEffect } from 'react'
import { useSearchParams } from 'next/navigation'
import { useAppStore } from '@/store/useAppStore'
import { useTransactions } from '@/hooks/useTransactions'
import { formatVND } from '@/lib/utils'
import { Transaction } from '@/types'
import { PageTransition } from '@/components/ui/PageTransition'

import { TransactionFilters } from './components/TransactionFilters'
import { TransactionList } from './components/TransactionList'
import { Pagination } from './components/Pagination'
import { DetailSidePanel } from './components/DetailSidePanel'
import { ConfirmModal } from '@/components/ui/ConfirmModal'

export function TransactionsPage() {
  const { openEditTransaction, openAddTransaction } = useAppStore()

  const {
    transactions, total, page, totalPages, isLoading, accounts, categories,
    filters, setPage, deleteTransaction
  } = useTransactions()

  const [selectedTx, setSelectedTx] = useState<Transaction | null>(null)
  const [deleteId, setDeleteId] = useState<string | null>(null)
  const searchParams = useSearchParams()

  useEffect(() => {
    if (searchParams.get('action') === 'transfer') {
      openAddTransaction('transfer')
      window.history.replaceState(null, '', '/transactions')
    }
  }, [searchParams, openAddTransaction])

  const totalIncome = transactions.filter(t => t.type === 'income').reduce((s, t) => s + t.amount, 0)
  const totalExpense = transactions.filter(t => t.type === 'expense').reduce((s, t) => s + t.amount, 0)

  async function confirmDelete() {
    if (!deleteId) return
    const tx = transactions.find(t => t.id === deleteId)
    await deleteTransaction(deleteId, tx)
    if (selectedTx?.id === deleteId) setSelectedTx(null)
    setDeleteId(null)
  }

  return (
    <PageTransition>
      <div className="transactions-shell">
        {/* Main content */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ marginBottom: 'var(--space-5)' }}>
            <h1 style={{ fontSize: 'var(--text-2xl)', fontWeight: 700, marginBottom: 'var(--space-1)' }}>Transactions</h1>
            <div style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: 'var(--space-2)', flexWrap: 'wrap' }}>
              <span>{total} transactions</span>
              <span style={{ color: 'var(--text-tertiary)' }}>|</span>
              <span style={{ color: 'var(--accent-green)', fontWeight: 600 }}>+{formatVND(totalIncome)}</span>
              <span style={{ color: 'var(--text-tertiary)' }}>income</span>
              <span style={{ color: 'var(--text-tertiary)' }}>·</span>
              <span style={{ color: 'var(--accent-red)', fontWeight: 600 }}>-{formatVND(totalExpense)}</span>
              <span style={{ color: 'var(--text-tertiary)' }}>expense</span>
              <span style={{ color: 'var(--text-tertiary)' }}>(page {page}/{totalPages})</span>
            </div>
          </div>

          <TransactionFilters
            filters={filters}
            accounts={accounts}
            categories={categories}
          />

          <TransactionList
            transactions={transactions}
            isLoading={isLoading}
            onAdd={openAddTransaction}
            onSelect={setSelectedTx}
            onEdit={openEditTransaction}
            onDelete={setDeleteId}
          />

          <Pagination page={page} totalPages={totalPages} setPage={setPage} />
        </div>

        <DetailSidePanel
          transaction={selectedTx}
          onClose={() => setSelectedTx(null)}
          onEdit={openEditTransaction}
          onDelete={setDeleteId}
        />

        <ConfirmModal
          isOpen={!!deleteId}
          onClose={() => setDeleteId(null)}
          onConfirm={confirmDelete}
          title="Delete transactions?"
          description="This action can be undone within 3 seconds."
        />
      </div>
      <style jsx>{`
        .transactions-shell {
          display: flex;
          gap: var(--space-6);
          align-items: flex-start;
        }

        @media (max-width: 1180px) {
          .transactions-shell {
            flex-direction: column;
          }

          .transactions-shell > :global(*) {
            width: 100%;
          }
        }
      `}</style>
    </PageTransition>
  )
}
