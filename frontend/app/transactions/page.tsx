import { Suspense } from 'react'
import { AppLayout } from '@/components/layout/AppLayout'
import { TransactionsPage } from '@/components/transactions/TransactionsPage'

export default function Transactions() {
  return (
    <AppLayout>
      <Suspense><TransactionsPage /></Suspense>
    </AppLayout>
  )
}
