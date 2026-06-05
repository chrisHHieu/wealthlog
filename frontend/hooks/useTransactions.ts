import { useState, useMemo } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useSearchParams } from 'next/navigation'
import { useToast } from '@/components/ui/toaster'
import { Transaction, PaginatedResponse } from '@/types'
import { apiDelete, apiGet, apiJson, queryKeys } from '@/lib/api'

const PAGE_SIZE = 10

interface Account {
  id: string
  name: string
  icon: string
}

interface Category {
  id: string
  name: string
  icon: string
}

export function useTransactions() {
  const qc = useQueryClient()
  const { toast } = useToast()
  const searchParams = useSearchParams()

  const [search, setSearch] = useState('')
  const [typeFilter, setTypeFilter] = useState(searchParams.get('type') || '')
  const [accountFilter, setAccountFilter] = useState(searchParams.get('accountId') || '')
  const [categoryFilter, setCategoryFilter] = useState('')
  const [selectedMonth, setSelectedMonth] = useState('')
  const [page, setPage] = useState(1)

  function resetPage() { setPage(1) }

  function handleSearchChange(val: string) { setSearch(val); resetPage() }
  function handleTypeChange(val: string) { setTypeFilter(val); resetPage() }
  function handleAccountChange(val: string) { setAccountFilter(val); resetPage() }
  function handleCategoryChange(val: string) { setCategoryFilter(val); resetPage() }
  function handleMonthChange(val: string) { setSelectedMonth(val); resetPage() }

  const params = useMemo(() => {
    return {
      page,
      pageSize: PAGE_SIZE,
      type: typeFilter || undefined,
      accountId: accountFilter || undefined,
      categoryId: categoryFilter || undefined,
      startDate: selectedMonth ? `${selectedMonth}-01` : undefined,
      endDate: selectedMonth ? `${selectedMonth}-31` : undefined,
      search: search || undefined,
    }
  }, [page, typeFilter, accountFilter, categoryFilter, selectedMonth, search])

  const { data: response, isLoading } = useQuery<PaginatedResponse<Transaction>>({
    queryKey: queryKeys.transactions(
      typeFilter,
      accountFilter,
      categoryFilter,
      selectedMonth,
      search,
      page,
    ),
    queryFn: () => apiGet<PaginatedResponse<Transaction>>('/api/transactions', params),
  })

  const { data: accounts = [] } = useQuery<Account[]>({
    queryKey: queryKeys.accounts,
    queryFn: () => apiGet<Account[]>('/api/accounts'),
  })

  const categoryParams = useMemo(() => {
    return {
      usedOnly: 1,
      startDate: selectedMonth ? `${selectedMonth}-01` : undefined,
      endDate: selectedMonth ? `${selectedMonth}-31` : undefined,
    }
  }, [selectedMonth])

  const { data: categories = [] } = useQuery<Category[]>({
    queryKey: queryKeys.categories(selectedMonth),
    queryFn: () => apiGet<Category[]>('/api/categories', categoryParams),
  })

  const transactions = response?.data ?? []
  const total = response?.total ?? 0
  const totalPages = response?.totalPages ?? 1

  async function deleteTransaction(id: string, txData?: Transaction) {
    await apiDelete(`/api/transactions/${id}`)
    await Promise.all([
      qc.invalidateQueries({ queryKey: ['transactions'] }),
      qc.invalidateQueries({ queryKey: ['dashboard'] }),
      qc.invalidateQueries({ queryKey: queryKeys.accounts }),
    ])

    toast('Transaction deleted', {
      type: 'success',
      undo: async () => {
        if (!txData) return
        await apiJson('/api/transactions', {
          method: 'POST',
          body: txData,
        })
        await Promise.all([
          qc.invalidateQueries({ queryKey: ['transactions'] }),
          qc.invalidateQueries({ queryKey: ['dashboard'] }),
          qc.invalidateQueries({ queryKey: queryKeys.accounts }),
        ])
      },
    })
  }

  return {
    transactions,
    total,
    page,
    totalPages,
    isLoading,
    accounts,
    categories,
    filters: {
      search, handleSearchChange,
      typeFilter, handleTypeChange,
      accountFilter, handleAccountChange,
      categoryFilter, handleCategoryChange,
      selectedMonth, handleMonthChange,
    },
    setPage,
    deleteTransaction
  }
}
