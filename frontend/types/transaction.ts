export interface Transaction {
  id: string
  type: 'income' | 'expense' | 'transfer' | string
  amount: number
  description?: string
  note?: string
  date: string
  accountId?: string
  accountName?: string
  accountIcon?: string
  categoryId?: string
  categoryName?: string
  categoryIcon?: string
  categoryColor?: string
}

export interface PaginatedResponse<T = Transaction> {
  data: T[]
  total: number
  page: number
  pageSize: number
  totalPages: number
}
