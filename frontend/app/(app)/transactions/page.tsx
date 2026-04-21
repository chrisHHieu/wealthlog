import { Suspense } from 'react'
import { TransactionsPage } from '@/components/transactions/TransactionsPage'

export default function Transactions() {
  return (
    <Suspense>
      <TransactionsPage />
    </Suspense>
  )
}
