import { useState, useMemo } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useToast } from '@/components/ui/toaster'
import { Transaction, PaginatedResponse } from '@/types'
import { API_URL } from '@/lib/api'

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

import { useSearchParams } from 'next/navigation'

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
    const p = new URLSearchParams()
    p.set('page', String(page))
    p.set('pageSize', String(PAGE_SIZE))
    if (typeFilter) p.set('type', typeFilter)
    if (accountFilter) p.set('accountId', accountFilter)
    if (categoryFilter) p.set('categoryId', categoryFilter)
    if (selectedMonth) {
      p.set('startDate', `${selectedMonth}-01`)
      p.set('endDate', `${selectedMonth}-31`)
    }
    if (search) p.set('search', search)
    return p
  }, [page, typeFilter, accountFilter, categoryFilter, selectedMonth, search])

  const { data: response, isLoading } = useQuery<PaginatedResponse<Transaction>>({
    queryKey: ['transactions', typeFilter, accountFilter, categoryFilter, selectedMonth, search, page],
    queryFn: () => fetch(`${API_URL}/api/transactions?${params}`).then(r => r.json()),
  })

  const { data: accounts = [] } = useQuery<Account[]>({
    queryKey: ['accounts'],
    queryFn: () => fetch(`${API_URL}/api/accounts`).then(r => r.json()),
  })

  const categoryParams = useMemo(() => {
    const p = new URLSearchParams()
    p.set('usedOnly', '1')
    if (selectedMonth) {
      p.set('startDate', `${selectedMonth}-01`)
      p.set('endDate', `${selectedMonth}-31`)
    }
    return `?${p}`
  }, [selectedMonth])

  const { data: categories = [] } = useQuery<Category[]>({
    queryKey: ['categories', selectedMonth],
    queryFn: () => fetch(`${API_URL}/api/categories${categoryParams}`).then(r => r.json()),
  })

  const transactions = response?.data ?? []
  const total = response?.total ?? 0
  const totalPages = response?.totalPages ?? 1

  async function deleteTransaction(id: string, txData?: Transaction) {
    await fetch(`${API_URL}/api/transactions/${id}`, { method: 'DELETE' })
    await Promise.all([
      qc.invalidateQueries({ queryKey: ['transactions'] }),
      qc.invalidateQueries({ queryKey: ['dashboard'] }),
      qc.invalidateQueries({ queryKey: ['accounts'] }),
    ])

    toast('Đã xóa giao dịch', {
      type: 'success',
      undo: async () => {
        if (!txData) return
        await fetch(`${API_URL}/api/transactions`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(txData),
        })
        await Promise.all([
          qc.invalidateQueries({ queryKey: ['transactions'] }),
          qc.invalidateQueries({ queryKey: ['dashboard'] }),
          qc.invalidateQueries({ queryKey: ['accounts'] }),
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
