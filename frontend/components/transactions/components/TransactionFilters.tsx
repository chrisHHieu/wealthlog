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
          placeholder="Tìm kiếm giao dịch (Mô tả, ghi chú)..."
          className="input"
          style={{ paddingLeft: 40, height: 44, fontSize: 14, borderRadius: 12 }}
        />
      </div>

      {/* Bottom row: Compact Filters */}
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>

      {/* Dropdowns */}
      <div style={{ zIndex: 10 }}>
        <Select
          value={typeFilter}
          onChange={handleTypeChange}
          placeholder="Tất cả loại"
          minWidth={130}
          options={[
            { value: '', label: 'Tất cả loại' },
            { value: 'income', label: 'Thu nhập' },
            { value: 'expense', label: 'Chi tiêu' },
            { value: 'transfer', label: 'Chuyển khoản' },
          ]}
        />
      </div>

      <div style={{ zIndex: 9 }}>
        <Select
          value={accountFilter}
          onChange={handleAccountChange}
          placeholder="Tất cả tài khoản"
          minWidth={160}
          options={[
            { value: '', label: 'Tất cả tài khoản' },
            ...accounts.map(a => ({ value: a.id, label: <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>{a.icon} {a.name}</span> }))
          ]}
        />
      </div>

      <div style={{ zIndex: 8 }}>
        <Select
          value={categoryFilter}
          onChange={handleCategoryChange}
          placeholder="Tất cả danh mục"
          minWidth={160}
          options={[
            { value: '', label: 'Tất cả danh mục' },
            ...categories.map(c => ({ value: c.id, label: <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>{c.icon} {c.name}</span> }))
          ]}
        />
      </div>

      <div style={{ zIndex: 11 }}>
        <MonthPicker
          value={selectedMonth}
          onChange={handleMonthChange}
        />
      </div>
    </div>
  </div>
  )
}
