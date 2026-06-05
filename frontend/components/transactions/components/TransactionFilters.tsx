import { Search } from 'lucide-react'
import { Select } from '@/components/ui/Select'
import { MonthPicker } from '@/components/ui/MonthPicker'
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

interface TransactionFiltersProps {
  filters: {
    search: string
    handleSearchChange: (v: string) => void
    typeFilter: string
    handleTypeChange: (v: string) => void
    accountFilter: string
    handleAccountChange: (v: string) => void
    categoryFilter: string
    handleCategoryChange: (v: string) => void
    selectedMonth: string
    handleMonthChange: (v: string) => void
  }
  accounts: Account[]
  categories: Category[]
}

export function TransactionFilters({ filters, accounts, categories }: TransactionFiltersProps) {
  const {
    search, handleSearchChange,
    typeFilter, handleTypeChange,
    accountFilter, handleAccountChange,
    categoryFilter, handleCategoryChange,
    selectedMonth, handleMonthChange,
  } = filters

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12, marginBottom: 20 }}>
      {/* Top row: Big Search Bar */}
      <div style={{ position: 'relative', width: '100%' }}>
        <Search size={16} style={{ position: 'absolute', left: 14, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-tertiary)' }} />
        <input
          id="tx-search"
          type="text"
          value={search}
          onChange={e => handleSearchChange(e.target.value)}
          placeholder="Search transactions (description, note)..."
          className="input"
          style={{ paddingLeft: 40, height: 44, fontSize: 14, borderRadius: 12 }}
        />
      </div>

      {/* Bottom row: Compact Filters */}
      <div className="transaction-filter-grid">

      {/* Dropdowns */}
      <div style={{ zIndex: 10, minWidth: 0 }}>
        <Select
          value={typeFilter}
          onChange={handleTypeChange}
          placeholder="All types"
          minWidth={130}
          options={[
            { value: '', label: 'All types' },
            { value: 'income', label: 'Income' },
            { value: 'expense', label: 'Expense' },
            { value: 'transfer', label: 'Transfer' },
          ]}
        />
      </div>

      <div style={{ zIndex: 9, minWidth: 0 }}>
        <Select
          value={accountFilter}
          onChange={handleAccountChange}
          placeholder="All accounts"
          minWidth={160}
          options={[
            { value: '', label: 'All accounts' },
            ...accounts.map(a => ({ value: a.id, label: <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>{a.icon} {a.name}</span> }))
          ]}
        />
      </div>

      <div style={{ zIndex: 8, minWidth: 0 }}>
        <Select
          value={categoryFilter}
          onChange={handleCategoryChange}
          placeholder="All categories"
          minWidth={160}
          options={[
            { value: '', label: 'All categories' },
            ...categories.map(c => ({ value: c.id, label: <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>{c.icon} {c.name}</span> }))
          ]}
        />
      </div>

      <div style={{ zIndex: 11, minWidth: 0 }}>
        <MonthPicker
          value={selectedMonth}
          onChange={handleMonthChange}
        />
      </div>
    </div>
    <style jsx>{`
      .transaction-filter-grid {
        display: grid;
        grid-template-columns: repeat(4, minmax(150px, max-content));
        gap: 8px;
        align-items: start;
      }

      @media (max-width: 900px) {
        .transaction-filter-grid {
          grid-template-columns: repeat(2, minmax(0, 1fr));
        }
      }

      @media (max-width: 520px) {
        .transaction-filter-grid {
          grid-template-columns: 1fr;
        }
      }
    `}</style>
  </div>
  )
}
