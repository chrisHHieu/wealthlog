import { useEffect, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'

import { useToast } from '@/components/ui/toaster'
import { useAppStore } from '@/store/useAppStore'
import { apiGet, apiJson, queryKeys } from '@/lib/api'
import { formatVND, getToday, parseShorthandAmount } from '@/lib/utils'

import { Account, BudgetStatus, Category, TransactionEditData, TxType } from './types'

export function useTransactionDrawerForm() {
  const {
    addTransactionOpen,
    transactionDefaultType,
    editTransactionId,
    closeAddTransaction,
  } = useAppStore()
  const { toast } = useToast()
  const queryClient = useQueryClient()

  const [txType, setTxType] = useState<TxType>('expense')
  const [amountRaw, setAmountRaw] = useState('')
  const [description, setDescription] = useState('')
  const [accountId, setAccountId] = useState('')
  const [toAccountId, setToAccountId] = useState('')
  const [categoryId, setCategoryId] = useState('')
  const [date, setDate] = useState(getToday())
  const [note, setNote] = useState('')
  const [saving, setSaving] = useState(false)
  const [saveAndAdd, setSaveAndAdd] = useState(false)

  const { data: accounts = [] } = useQuery<Account[]>({
    queryKey: queryKeys.accounts,
    queryFn: () => apiGet<Account[]>('/api/accounts'),
  })

  const { data: categories = [] } = useQuery<Category[]>({
    queryKey: queryKeys.categories(),
    queryFn: () => apiGet<Category[]>('/api/categories'),
  })

  const { data: editData } = useQuery<TransactionEditData>({
    queryKey: queryKeys.transaction(editTransactionId),
    queryFn: () => apiGet<TransactionEditData>(`/api/transactions/${editTransactionId}`),
    enabled: !!editTransactionId,
  })

  function resetForm() {
    setTxType(transactionDefaultType || 'expense')
    setAmountRaw('')
    setDescription('')
    setNote('')
    setCategoryId('')
    setDate(getToday())
    setToAccountId('')
  }

  useEffect(() => {
    if (!addTransactionOpen) return
    if (editTransactionId && editData) {
      setTxType(editData.type)
      setAmountRaw(String(editData.amount))
      setDescription(editData.description)
      setAccountId(editData.accountId)
      setToAccountId(editData.type === 'transfer' && editData.toAccountId ? editData.toAccountId : '')
      setCategoryId(editData.categoryId || '')
      setDate(editData.date.substring(0, 10))
      setNote(editData.note || '')
    } else if (!editTransactionId) {
      resetForm()
    }
  }, [addTransactionOpen, editTransactionId, editData, transactionDefaultType])

  useEffect(() => {
    if (accounts.length > 0 && !accountId && !editTransactionId) {
      setAccountId(accounts[0].id)
    }
  }, [accounts, accountId, editTransactionId])

  const filteredCategories = categories.filter(
    category => category.type === txType || category.type === 'both',
  )
  const parsedAmount = parseShorthandAmount(amountRaw) ?? 0
  const isValid = parsedAmount > 0 && description.trim() && accountId &&
    (txType !== 'transfer' || (toAccountId && toAccountId !== accountId))

  async function handleSubmit(addMore = false) {
    if (!isValid) return
    setSaving(true)
    setSaveAndAdd(addMore)

    try {
      const body = {
        type: txType,
        amount: parsedAmount,
        accountId,
        toAccountId: txType === 'transfer' ? toAccountId || undefined : undefined,
        categoryId: categoryId || undefined,
        description: description.trim(),
        date,
        note: note.trim() || undefined,
      }

      await apiJson(
        editTransactionId ? `/api/transactions/${editTransactionId}` : '/api/transactions',
        { method: editTransactionId ? 'PUT' : 'POST', body },
      )

      await queryClient.invalidateQueries({ queryKey: ['transactions'] })
      await queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      await queryClient.invalidateQueries({ queryKey: queryKeys.accounts })

      toast(editTransactionId ? 'Transaction updated' : 'Transaction added')
      await maybeShowBudgetWarning()

      if (addMore) {
        setAmountRaw('')
        setDescription('')
        setNote('')
        setDate(getToday())
        setCategoryId('')
      } else {
        closeAddTransaction()
      }
    } finally {
      setSaving(false)
      setSaveAndAdd(false)
    }
  }

  async function maybeShowBudgetWarning() {
    if (txType !== 'expense' || !categoryId) return
    try {
      const budgetStatus = await apiGet<BudgetStatus>('/api/budgets/check', {
        categoryId,
        month: date.substring(0, 7),
      })
      if (budgetStatus?.isExceeded) {
        toast(
          `Budget exceeded ${budgetStatus.categoryIcon} ${budgetStatus.categoryName}! Spent ${formatVND(budgetStatus.totalSpent)} / ${formatVND(budgetStatus.budgetAmount)} (${budgetStatus.percent}%)`,
          { type: 'error', duration: 5000 },
        )
      } else if (budgetStatus?.isWarning) {
        toast(
          `Budget almost used ${budgetStatus.categoryIcon} ${budgetStatus.categoryName}: left ${formatVND(budgetStatus.remaining)} (${budgetStatus.percent}%)`,
          { type: 'info', duration: 4000 },
        )
      }
    } catch {
      // Silently ignore budget check errors
    }
  }

  return {
    accounts,
    addTransactionOpen,
    amountRaw,
    categoryId,
    closeAddTransaction,
    date,
    description,
    editTransactionId,
    filteredCategories,
    handleSubmit,
    isValid,
    accountId,
    saveAndAdd,
    saving,
    setAccountId,
    setAmountRaw,
    setCategoryId,
    setDate,
    setDescription,
    setToAccountId,
    setTxType,
    toAccountId,
    txType,
  }
}
