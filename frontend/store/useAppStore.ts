'use client'

import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface AppState {
  // UI State
  sidebarCollapsed: boolean
  mobileMenuOpen: boolean
  theme: 'dark' | 'light'
  
  // Modal/Drawer State
  addTransactionOpen: boolean
  transactionDefaultType: 'income' | 'expense' | 'transfer' | null
  editTransactionId: string | null
  addAccountOpen: boolean
  editAccountId: string | null
  addGoalOpen: boolean
  editGoalId: string | null
  addBudgetOpen: boolean
  addInvestmentOpen: boolean
  editInvestmentId: string | null
  
  // Chat State
  chatOpen: boolean

  // Actions
  toggleSidebar: () => void
  setMobileMenu: (open: boolean) => void
  setTheme: (theme: 'dark' | 'light') => void
  toggleTheme: () => void
  
  toggleChat: () => void
  openChat: () => void
  closeChat: () => void

  openAddTransaction: (type?: 'income' | 'expense' | 'transfer') => void
  closeAddTransaction: () => void
  openEditTransaction: (id: string) => void
  closeEditTransaction: () => void
  
  openAddAccount: () => void
  closeAddAccount: () => void
  openEditAccount: (id: string) => void
  closeEditAccount: () => void
  
  openAddGoal: () => void
  closeAddGoal: () => void
  openEditGoal: (id: string) => void
  closeEditGoal: () => void
  
  openAddBudget: () => void
  closeAddBudget: () => void
  
  openAddInvestment: () => void
  closeAddInvestment: () => void
  openEditInvestment: (id: string) => void
  closeEditInvestment: () => void
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      sidebarCollapsed: false,
      mobileMenuOpen: false,
      theme: 'dark',
      addTransactionOpen: false,
      transactionDefaultType: null,
      editTransactionId: null,
      addAccountOpen: false,
      editAccountId: null,
      addGoalOpen: false,
      editGoalId: null,
      addBudgetOpen: false,
      addInvestmentOpen: false,
      editInvestmentId: null,
      
      chatOpen: false,

      toggleSidebar: () => set(s => ({ sidebarCollapsed: !s.sidebarCollapsed })),
      setMobileMenu: (open) => set({ mobileMenuOpen: open }),
      setTheme: (theme) => set({ theme }),
      toggleTheme: () => set(s => ({ theme: s.theme === 'dark' ? 'light' : 'dark' })),
      
      toggleChat: () => set(s => ({ chatOpen: !s.chatOpen })),
      openChat: () => set({ chatOpen: true }),
      closeChat: () => set({ chatOpen: false }),

      openAddTransaction: (type) => set({ addTransactionOpen: true, transactionDefaultType: type || null, editTransactionId: null }),
      closeAddTransaction: () => set({ addTransactionOpen: false, transactionDefaultType: null, editTransactionId: null }),
      openEditTransaction: (id) => set({ editTransactionId: id, addTransactionOpen: true }),
      closeEditTransaction: () => set({ editTransactionId: null, addTransactionOpen: false }),
      
      openAddAccount: () => set({ addAccountOpen: true, editAccountId: null }),
      closeAddAccount: () => set({ addAccountOpen: false }),
      openEditAccount: (id) => set({ addAccountOpen: true, editAccountId: id }),
      closeEditAccount: () => set({ addAccountOpen: false, editAccountId: null }),
      
      openAddGoal: () => set({ addGoalOpen: true, editGoalId: null }),
      closeAddGoal: () => set({ addGoalOpen: false }),
      openEditGoal: (id) => set({ addGoalOpen: true, editGoalId: id }),
      closeEditGoal: () => set({ addGoalOpen: false, editGoalId: null }),
      
      openAddBudget: () => set({ addBudgetOpen: true }),
      closeAddBudget: () => set({ addBudgetOpen: false }),
      
      openAddInvestment: () => set({ addInvestmentOpen: true, editInvestmentId: null }),
      closeAddInvestment: () => set({ addInvestmentOpen: false }),
      openEditInvestment: (id) => set({ addInvestmentOpen: true, editInvestmentId: id }),
      closeEditInvestment: () => set({ addInvestmentOpen: false, editInvestmentId: null }),
    }),
    {
      name: 'wealthlog-app',
      partialize: (state) => ({
        sidebarCollapsed: state.sidebarCollapsed,
        theme: state.theme,
      }),
    }
  )
)
