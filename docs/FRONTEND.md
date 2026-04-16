# 🎨 Frontend Architecture — WealthLog

## Mục Lục

- [Tổng Quan](#tổng-quan)
- [Tech Stack](#tech-stack)
- [Cấu Trúc Thư Mục](#cấu-trúc-thư-mục)
- [App Router & Routing](#app-router--routing)
- [Design System](#design-system)
- [Component Architecture](#component-architecture)
- [State Management](#state-management)
- [Data Fetching](#data-fetching)
- [Form Handling](#form-handling)
- [UI Components Library](#ui-components-library)
- [Type System](#type-system)
- [Utilities](#utilities)

---

## Tổng Quan

Frontend WealthLog được xây dựng trên **Next.js 16** (App Router) với kiến trúc **component-based**, sử dụng:

- **TanStack Query** cho server state
- **Zustand** cho client state
- **Tailwind CSS 4** + CSS Custom Properties cho styling
- **Recharts** cho data visualization
- **Radix UI** cho accessible primitives
- **React Hook Form + Zod** cho form validation

---

## Tech Stack

```
Next.js 16 (App Router)
├── React 19
├── TypeScript 5
├── Tailwind CSS 4 + CSS Custom Properties
├── TanStack Query 5 (Server State)
├── Zustand 5 (Client State, persisted)
├── Recharts 3 (Charts)
├── React Hook Form 7 + Zod 4 (Forms)
├── Framer Motion 12 (Animations)
├── Radix UI (Accessible Primitives)
├── Lucide React (Icons)
└── ExcelJS + PapaParse (Data Export)
```

---

## Cấu Trúc Thư Mục

```
frontend/
├── app/                          # Next.js App Router
│   ├── layout.tsx                # Root layout (font, metadata, providers)
│   ├── page.tsx                  # Home → Dashboard
│   ├── providers.tsx             # QueryClient + Theme + Toast
│   ├── globals.css               # Design system (749 lines)
│   ├── accounts/page.tsx         # Accounts page
│   ├── budget/page.tsx           # Budget page
│   ├── goals/page.tsx            # Goals page
│   ├── investments/page.tsx      # Investments page
│   ├── recurring/page.tsx        # Recurring page
│   ├── reports/page.tsx          # Reports page
│   ├── settings/page.tsx         # Settings page
│   └── transactions/page.tsx     # Transactions page
│
├── components/                   # React Components
│   ├── layout/                   # App shell
│   │   ├── AppLayout.tsx         # Main layout wrapper
│   │   ├── Sidebar.tsx           # Navigation sidebar (collapsible)
│   │   ├── Header.tsx            # Top header bar
│   │   └── FAB.tsx               # Floating action button
│   │
│   ├── dashboard/                # Dashboard feature
│   │   ├── Dashboard.tsx         # Main dashboard component
│   │   └── components/
│   │       ├── KPICards.tsx       # Income/Expense/Savings/NetWorth cards
│   │       ├── CashFlowChart.tsx  # Monthly income vs expense bar chart
│   │       ├── SpendingBreakdown.tsx  # Category pie chart + 50/30/20
│   │       ├── AssetLiability.tsx # Assets vs Liabilities breakdown
│   │       ├── BudgetProgress.tsx # Budget progress bars
│   │       ├── GoalsSnapshot.tsx  # Active goals mini-cards
│   │       ├── RecentTransactions.tsx # Latest 7 transactions
│   │       └── UpcomingBills.tsx  # Next 30 days recurring bills
│   │
│   ├── transactions/             # Transaction management
│   │   ├── TransactionsPage.tsx  # Main transactions page
│   │   ├── TransactionDrawer.tsx # Create/Edit drawer (14.7KB)
│   │   └── components/
│   │       ├── TransactionList.tsx    # Transaction list table
│   │       ├── TransactionFilters.tsx # Filter bar
│   │       ├── Pagination.tsx        # Page navigation
│   │       └── DetailSidePanel.tsx   # Transaction detail panel
│   │
│   ├── accounts/
│   │   └── AccountsPage.tsx      # Full account CRUD (19.9KB)
│   │
│   ├── budget/
│   │   └── BudgetPage.tsx        # Budget management (18.9KB)
│   │
│   ├── goals/
│   │   ├── GoalsPage.tsx         # Goals list page
│   │   └── components/
│   │       ├── GoalCard.tsx          # Individual goal card
│   │       ├── GoalFormDrawer.tsx    # Create/Edit goal drawer
│   │       ├── ContributeModal.tsx   # Add contribution modal
│   │       └── CompletedGoalCard.tsx # Completed goal display
│   │
│   ├── investments/
│   │   └── InvestmentsPage.tsx   # Investment portfolio (18KB)
│   │
│   ├── recurring/
│   │   ├── RecurringPage.tsx     # Recurring transactions list
│   │   └── RecurringDrawer.tsx   # Create/Edit recurring drawer
│   │
│   ├── reports/
│   │   ├── ReportsPage.tsx       # Reports page wrapper
│   │   └── components/
│   │       ├── ReportHeader.tsx      # Period selector + KPIs
│   │       ├── ComparisonKPIs.tsx    # Income/Expense/Savings comparison
│   │       ├── IncomeExpenseChart.tsx # Bar chart
│   │       ├── SpendingTrend.tsx     # Cumulative expense trend
│   │       ├── PeriodComparison.tsx  # Category comparison tables
│   │       └── CashFlowStatement.tsx # Cash flow report
│   │
│   ├── settings/
│   │   └── SettingsPage.tsx      # Settings + Category management (20KB)
│   │
│   ├── ui/                       # Reusable UI primitives
│   │   ├── AmountInput.tsx       # Vietnamese currency input with auto-format
│   │   ├── AnimatedCounter.tsx   # Smooth number animation
│   │   ├── BankLogo.tsx          # Vietnamese bank logo mapping
│   │   ├── CircularProgress.tsx  # SVG circular progress indicator
│   │   ├── ConfirmModal.tsx      # Confirmation dialog
│   │   ├── CustomTooltip.tsx     # Recharts tooltip override
│   │   ├── DatePicker.tsx        # Custom date picker
│   │   ├── MonthNavigator.tsx    # Month forward/backward navigation
│   │   ├── MonthPicker.tsx       # Month/Year picker modal
│   │   ├── Portal.tsx            # React Portal wrapper
│   │   ├── Select.tsx            # Custom dropdown select
│   │   ├── SkeletonKPI.tsx       # KPI loading skeleton
│   │   └── toaster.tsx           # Toast notification system (undo support)
│   │
│   └── providers/
│       └── ThemeProvider.tsx     # Dark/Light theme toggle
│
├── hooks/                        # Custom React Hooks
│   ├── useDashboard.ts          # Dashboard data + KPI computations
│   ├── useTransactions.ts       # Paginated transactions + CRUD
│   ├── useReports.ts            # Reports data + period navigation
│   └── useGoals.ts              # Goals list query
│
├── lib/                          # Utilities & Configuration
│   ├── api.ts                   # API base URL
│   ├── utils.ts                 # Formatting, date, currency utilities
│   └── validations.ts           # Zod schemas for all forms
│
├── store/                        # Global State
│   └── useAppStore.ts           # Zustand store (UI state)
│
└── types/                        # TypeScript Interfaces
    ├── index.ts                 # Re-exports
    ├── transaction.ts           # Transaction + PaginatedResponse
    ├── dashboard.ts             # DashboardData
    ├── reports.ts               # ReportsData, ChartPoint, CashFlow...
    └── goal.ts                  # Goal
```

---

## App Router & Routing

### Root Layout (`app/layout.tsx`)

```tsx
// Cấu hình:
// - Font: Geist Sans (Google Fonts)
// - Language: Vietnamese (lang="vi")
// - Metadata: SEO-optimized
// - Providers: QueryClient + Theme + Toast
```

### Providers (`app/providers.tsx`)

```
QueryClientProvider          ← TanStack Query (staleTime: 30s)
  └── ThemeProvider          ← Dark/Light mode (data-theme attribute)
       └── Toaster           ← Toast notification system
            └── {children}   ← Page content
```

### Page Pattern

Mỗi route page là **thin wrapper** — chỉ import layout + feature component:

```tsx
// Ví dụ: app/transactions/page.tsx
'use client'
import { AppLayout } from '@/components/layout/AppLayout'
import { TransactionsPage } from '@/components/transactions/TransactionsPage'

export default function Page() {
  return (
    <AppLayout>
      <TransactionsPage />
    </AppLayout>
  )
}
```

### Route Map

| Path | Component | Mô tả |
|---|---|---|
| `/` | `Dashboard` | Tổng quan tài chính |
| `/transactions` | `TransactionsPage` | Danh sách giao dịch |
| `/accounts` | `AccountsPage` | Quản lý tài khoản |
| `/budget` | `BudgetPage` | Ngân sách theo danh mục |
| `/goals` | `GoalsPage` | Mục tiêu tiết kiệm |
| `/investments` | `InvestmentsPage` | Danh mục đầu tư |
| `/recurring` | `RecurringPage` | Giao dịch định kỳ |
| `/reports` | `ReportsPage` | Báo cáo phân tích |
| `/settings` | `SettingsPage` | Cài đặt ứng dụng |

---

## Design System

### CSS Architecture

Design system sử dụng **CSS Custom Properties** (Design Tokens) trong `globals.css`:

#### Color Palette

```css
/* Dark Mode (default) */
--bg-primary: #0F0F14;        /* Page background */
--bg-secondary: #16161f;      /* Card/Sidebar background */
--bg-tertiary: #1c1c28;       /* Nested surface */
--surface: rgba(255,255,255,0.04);
--text-primary: #f4f4f6;
--text-secondary: #8b8da0;
--text-tertiary: #5a5c6e;
--accent-green: #00C896;      /* Primary accent */
--accent-red: #FF4D6D;        /* Danger/expense */
--accent-blue: #3d8ef8;       /* Info */
--accent-yellow: #f59e0b;     /* Warning */
--accent-purple: #8b5cf6;     /* Secondary accent */

/* Light Mode ([data-theme="light"]) */
--bg-primary: #f8f9fc;
--bg-secondary: #ffffff;
--bg-tertiary: #f1f3f9;
--text-primary: #0f0f14;
--text-secondary: #5c5e70;
```

#### Typography

```css
--font-display: 'Instrument Serif', Georgia, serif;  /* Headlines, amounts */
--font-sans: var(--font-geist-sans), system-ui;       /* Body text */
```

#### Spacing & Radius

```css
--radius-sm: 8px;
--radius-md: 12px;
--radius-lg: 16px;
--radius-xl: 20px;
--sidebar-width: 240px;
--sidebar-width-collapsed: 64px;
--header-height: 64px;
```

### Component Classes

| Class | Mô tả |
|---|---|
| `.card` | Glass card with hover effect |
| `.card-glass` | Stronger glassmorphism |
| `.kpi-card` | Dashboard KPI card |
| `.btn` / `.btn-primary` / `.btn-secondary` / `.btn-danger` / `.btn-ghost` | Button variants |
| `.btn-sm` / `.btn-lg` | Button sizes |
| `.input` / `.input-amount` | Form inputs |
| `.label` | Form label |
| `.badge-green` / `.badge-red` / `.badge-blue` / `.badge-yellow` | Status badges |
| `.progress-bar` / `.progress-bar-fill` | Progress indicator |
| `.tabs` / `.tab-btn` | Tab navigation |
| `.drawer` / `.overlay` / `.modal` | Overlay components |
| `.skeleton` | Loading shimmer |
| `.toast` | Toast notification |
| `.fab` | Floating action button |
| `.table` | Data table |
| `.amount-positive` / `.amount-negative` | Color-coded amounts |
| `.category-icon` | Category icon badge |
| `.fade-in-up` / `.stagger-in` | Entrance animations |
| `.empty-state` | Empty data placeholder |
| `.divider` | Horizontal separator |

### Animation System

```css
/* Micro-animations */
fadeIn       — overlay entrance
slideInRight — drawer entrance
scaleIn      — modal entrance
slideUp      — toast entrance
shimmer      — skeleton loading
fadeInUp     — content entrance

/* Stagger animation */
.stagger-in > *:nth-child(n) — 60ms delay per child
```

---

## Component Architecture

### Layout Components

```
AppLayout
├── Sidebar           ← Fixed left, collapsible (240px ↔ 64px)
│   ├── Logo + Brand
│   ├── Navigation Links (with active state)
│   └── Theme Toggle + Collapse Button
├── Header            ← Fixed top, blur backdrop
│   ├── Page Title
│   └── User Actions
├── Main Content      ← Scrollable, max-width 1400px
│   └── {children}    ← Page component
└── FAB               ← Floating "+" button → open TransactionDrawer
```

### Dashboard Widgets

```
Dashboard
├── MonthPicker              ← Month selector + period dropdown
├── KPICards                 ← 4 cards: Income, Expense, Savings, Net Worth
│   └── AnimatedCounter      ← Smooth number transition
├── CashFlowChart            ← Recharts BarChart (income vs expense)
├── SpendingBreakdown        ← PieChart + 50/30/20 bars + category list
├── AssetLiability           ← Assets vs Liabilities stacked display
├── BudgetProgress           ← Progress bars per category
├── GoalsSnapshot            ← Active goals with circular progress
├── RecentTransactions       ← Latest 7 transactions list
└── UpcomingBills            ← Next 30 days bills
```

### Transaction Flow

```
TransactionsPage
├── TransactionFilters       ← Search, Type, Account, Category, Month
├── TransactionList          ← Paginated table with actions
│   ├── Click row → DetailSidePanel
│   ├── Edit button → TransactionDrawer (edit mode)
│   └── Delete button → ConfirmModal → Undo Toast
├── Pagination               ← Page navigation controls
└── TransactionDrawer        ← Create/Edit form
    ├── Type selector (Income/Expense/Transfer tabs)
    ├── AmountInput (auto-formatted VND)
    ├── Account/Category selectors
    ├── DatePicker
    ├── Budget check warning (real-time)
    └── Submit/Cancel actions
```

---

## State Management

### TanStack Query (Server State)

Quản lý tất cả API data với auto-caching và invalidation:

```typescript
// Configuration
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,          // 30 seconds
      refetchOnWindowFocus: false, // Disable auto-refetch
    },
  },
})

// Query Keys
['dashboard', chartPeriod, selectedMonth]
['transactions', type, account, category, month, search, page]
['accounts']
['categories', month?]
['reports', mode, month, year]
['goals']
['budgets', month]
```

### Zustand (Client State)

Quản lý UI state, persisted to localStorage:

```typescript
interface AppState {
  // Persisted (localStorage)
  sidebarCollapsed: boolean
  theme: 'dark' | 'light'
  
  // Transient (reset on refresh)
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
  selectedAccountId: string | null
  selectedTransactionId: string | null
}
```

### Query Invalidation Strategy

Khi tạo/sửa/xóa data, các related queries được invalidated:

```
Transaction CRUD → invalidate ['transactions', 'dashboard', 'accounts']
Budget CRUD      → invalidate ['budgets', 'dashboard']
Account CRUD     → invalidate ['accounts', 'dashboard']
Goal CRUD        → invalidate ['goals']
```

---

## Data Fetching

### Custom Hooks

#### `useDashboard(chartPeriod, selectedMonth)`

```typescript
// Returns:
{
  data: DashboardData           // From /api/dashboard
  isLoading: boolean
  activeGoals: Goal[]           // Non-completed goals (max 3)
  stats: {
    incomeDiff: number          // Current - Previous income
    expenseDiff: number         // Current - Previous expense
    incomePct: string | null    // % change
    expensePct: string | null   // % change
  }
}
```

#### `useTransactions()`

```typescript
// Returns:
{
  transactions: Transaction[]
  total: number
  page: number
  totalPages: number
  isLoading: boolean
  accounts: Account[]
  categories: Category[]
  filters: {
    search, handleSearchChange,
    typeFilter, handleTypeChange,
    accountFilter, handleAccountChange,
    categoryFilter, handleCategoryChange,
    selectedMonth, handleMonthChange,
  }
  setPage: (page: number) => void
  deleteTransaction: (id: string, txData?: Transaction) => Promise<void>
}
```

#### `useReports()`

```typescript
// Returns:
{
  mode: 'month' | 'year'
  setMode: (mode: ReportMode) => void
  selectedMonth: string              // YYYY-MM
  setSelectedMonth: (m: string) => void
  selectedYear: number
  setSelectedYear: (y: number) => void
  isLoading: boolean
  data: ReportsData
}
```

---

## Form Handling

### Stack: React Hook Form + Zod

Mỗi form có Zod schema tương ứng trong `lib/validations.ts`:

```typescript
// Ví dụ: Transaction form
const transactionSchema = z.object({
  type: z.enum(['income', 'expense', 'transfer']),
  amount: z.number().positive('Số tiền phải lớn hơn 0'),
  accountId: z.string().min(1, 'Vui lòng chọn tài khoản'),
  toAccountId: z.string().optional(),
  categoryId: z.string().optional(),
  description: z.string().min(1, 'Vui lòng nhập mô tả'),
  note: z.string().optional(),
  tags: z.array(z.string()).optional(),
  date: z.string().min(1, 'Vui lòng chọn ngày'),
})
```

### Schemas Available

| Schema | Sử dụng cho |
|---|---|
| `transactionSchema` | TransactionDrawer |
| `accountSchema` | AccountsPage (inline drawer) |
| `budgetSchema` | BudgetPage |
| `goalSchema` | GoalFormDrawer |
| `investmentSchema` | InvestmentsPage |
| `categorySchema` | SettingsPage (category management) |

---

## UI Components Library

### AmountInput

Custom currency input với auto-format theo VND (1.234.567):
- Parse dots/commas khi submit
- Live formatting khi gõ
- Display font: Instrument Serif 32px

### DatePicker

Custom calendar picker:
- Hiển thị tháng hiện tại
- Navigation tháng trước/sau
- Chọn ngày, highlight ngày hiện tại
- Responsive dropdown positioning

### MonthPicker

Full month/year selector:
- Grid 12 tháng
- Navigation năm trước/sau
- Highlight tháng hiện tại

### Select

Custom dropdown thay thế native `<select>`:
- Theme-consistent styling
- Search/filter support
- Portal rendering (tránh overflow clipping)
- Keyboard navigation

### AnimatedCounter

Smooth số chạy animation:
- Transition từ giá trị cũ → mới
- Duration configurable
- Auto-format VND

### CircularProgress

SVG-based circular progress:
- Percentage display
- Color configurable
- Smooth transition

### Toast System

Custom toast notification:
- Success/Error variants
- **Undo support** — callback function on undo click
- Auto-dismiss (3 seconds)

---

## Type System

### Core Interfaces

```typescript
// Transaction
interface Transaction {
  id: string
  type: 'income' | 'expense' | 'transfer'
  amount: number
  description?: string
  note?: string
  date: string                    // YYYY-MM-DD
  accountId?: string
  accountName?: string
  categoryId?: string
  categoryName?: string
  categoryIcon?: string
  categoryColor?: string
}

// PaginatedResponse<T>
interface PaginatedResponse<T> {
  data: T[]
  total: number
  page: number
  pageSize: number
  totalPages: number
}

// Goal
interface Goal {
  id: string
  name: string
  type?: string
  targetAmount: number
  currentAmount: number
  deadline?: string
  icon: string
  color: string
  description?: string
  isCompleted?: boolean
}

// DashboardData — see types/dashboard.ts
// ReportsData — see types/reports.ts
```

---

## Utilities

### Currency Formatting (`lib/utils.ts`)

| Function | Example |
|---|---|
| `formatVND(1500000)` | `"1.500.000 đ"` |
| `formatVNDCompact(1500000)` | `"1.5 triệu"` |
| `formatVNDCompact(2000000000)` | `"2.0 tỷ"` |
| `parseShorthandAmount("1.234.567")` | `1234567` |
| `formatAmountLive("1234567")` | `"1.234.567"` |

### Date Formatting

| Function | Example |
|---|---|
| `formatDateVI("2026-04-16")` | `"16/04/2026"` |
| `formatRelativeDate("2026-04-16")` | `"Hôm nay"` |
| `formatMonthVI("2026-04")` | `"Tháng 4/2026"` |
| `getCurrentMonth()` | `"2026-04"` |
| `getToday()` | `"2026-04-16"` |
| `getGreeting()` | `"Chào buổi sáng"` |
| `getDaysRemaining("2026-12-31")` | `259` |

### Other Utilities

| Function | Mô tả |
|---|---|
| `calcMonthlySavingsNeeded(target, current, deadline)` | Tính số tiền tiết kiệm mỗi tháng |
| `cn(...inputs)` | Tailwind class merge utility (clsx + twMerge) |
