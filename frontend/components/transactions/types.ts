export interface Account {
  id: string
  name: string
  icon: string
  type: string
}

export interface Category {
  id: string
  name: string
  icon: string
  color: string
  type: string
}

export type TxType = 'income' | 'expense' | 'transfer'

export interface TransactionEditData {
  type: TxType
  amount: number
  description: string
  accountId: string
  toAccountId?: string
  categoryId?: string
  date: string
  note?: string
}

export interface BudgetStatus {
  isExceeded: boolean
  isWarning: boolean
  categoryIcon: string
  categoryName: string
  totalSpent: number
  budgetAmount: number
  percent: number
  remaining: number
}

export const TAB_COLORS: Record<TxType, string> = {
  income: 'var(--accent-green)',
  expense: 'var(--accent-red)',
  transfer: 'var(--accent-blue)',
}
