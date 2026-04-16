# 🏗 Kiến Trúc Hệ Thống — WealthLog

## Mục Lục

- [Tổng Quan Kiến Trúc](#tổng-quan-kiến-trúc)
- [Luồng Request](#luồng-request)
- [Backend Architecture](#backend-architecture)
- [Frontend Architecture](#frontend-architecture)
- [State Management](#state-management)
- [Design Patterns](#design-patterns)
- [Luồng Dữ Liệu Chính](#luồng-dữ-liệu-chính)
- [Error Handling](#error-handling)

---

## Tổng Quan Kiến Trúc

WealthLog sử dụng kiến trúc **Monorepo** với 2 ứng dụng chính:

```
┌──────────────────────────────────────────────────────────────────┐
│                          Client (Browser)                        │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                    Next.js 16 (App Router)                 │  │
│  │                                                            │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │  │
│  │  │ Dashboard │  │ Transact │  │  Budget  │  │ Reports  │  │  │
│  │  └─────┬────┘  └─────┬────┘  └─────┬────┘  └─────┬────┘  │  │
│  │        └──────────────┼──────────────┼──────────────┘       │  │
│  │                       ▼                                    │  │
│  │              ┌────────────────┐                            │  │
│  │              │ TanStack Query │ (Server State Cache)       │  │
│  │              └────────┬───────┘                            │  │
│  │              ┌────────┴───────┐                            │  │
│  │              │    Zustand     │ (UI State)                 │  │
│  │              └────────────────┘                            │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────┬───────────────────────────────────────┘
                           │ HTTP (REST API)
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│                       FastAPI Backend                             │
│                                                                  │
│  ┌─────────┐  ┌──────────┐  ┌──────────┐  ┌─────────────────┐  │
│  │ Routers │→ │ Schemas  │→ │ Services │→ │ Models (ORM)    │  │
│  │ (API)   │  │ (Pydanticv2)│ (Logic)  │  │ (SQLAlchemy 2)  │  │
│  └─────────┘  └──────────┘  └──────────┘  └────────┬────────┘  │
│                                                      │           │
│  ┌───────────────────────────────────────────────────┘           │
│  │ Alembic Migrations                                            │
│  └──────────────────────┬────────────────────────────────────────┘
                          │ asyncpg
                          ▼
┌──────────────────────────────────────────────────────────────────┐
│                    PostgreSQL 16 (Alpine)                         │
│                                                                  │
│  accounts │ transactions │ categories │ budgets │ goals          │
│  investments │ recurring_transactions │ settings                  │
│  goal_contributions                                              │
└──────────────────────────────────────────────────────────────────┘
```

---

## Luồng Request

### Ví dụ: Tạo giao dịch mới

```
Browser                    Frontend                    Backend                    Database
  │                           │                           │                           │
  │  User submits form        │                           │                           │
  │────────────────────────→  │                           │                           │
  │                           │  POST /api/transactions   │                           │
  │                           │────────────────────────→  │                           │
  │                           │                           │  Validate (Pydantic)      │
  │                           │                           │  Create Transaction       │
  │                           │                           │────────────────────────→  │
  │                           │                           │  Update Account Balance   │
  │                           │                           │────────────────────────→  │
  │                           │                           │  COMMIT                   │
  │                           │                           │←────────────────────────  │
  │                           │  TransactionResponse      │                           │
  │                           │←────────────────────────  │                           │
  │                           │  Invalidate queries:      │                           │
  │                           │  [transactions, dashboard,│                           │
  │                           │   accounts]               │                           │
  │  UI Updates               │                           │                           │
  │←────────────────────────  │                           │                           │
```

---

## Backend Architecture

### Layer Structure

```
Routers (HTTP layer)
    ↓
Schemas (Validation layer — Pydantic v2)
    ↓
Services (Business logic)
    ↓
Models (Data access — SQLAlchemy 2.0)
    ↓
Database (PostgreSQL via asyncpg)
```

### Routers (`app/routers/`)

Mỗi router tương ứng với một **domain module**:

| Router | Prefix | Chức năng |
|---|---|---|
| `accounts.py` | `/api/accounts` | CRUD tài khoản |
| `transactions.py` | `/api/transactions` | CRUD giao dịch + balance logic |
| `categories.py` | `/api/categories` | CRUD danh mục với filter `usedOnly` |
| `budgets.py` | `/api/budgets` | CRUD ngân sách + check endpoint |
| `goals.py` | `/api/goals` | CRUD mục tiêu + contribute |
| `investments.py` | `/api/investments` | CRUD đầu tư |
| `recurring.py` | `/api/recurring` | CRUD giao dịch định kỳ |
| `dashboard.py` | `/api/dashboard` | Aggregation endpoint cho dashboard |
| `reports.py` | `/api/reports` | Aggregation endpoint cho reports |
| `settings.py` | `/api/settings` | Key-value settings store |

### Services (`app/services/`)

| Service | Chức năng |
|---|---|
| `recurring_sync.py` | Tự động tạo giao dịch từ recurring rules khi đến hạn. Sử dụng `asyncio.Lock` để tránh race conditions. |
| `seed.py` | Seed dữ liệu mặc định (18 danh mục + 4 settings) vào DB trống. |

### Startup Flow

```
FastAPI app start
    │
    ├── setup_logging()          # Configure structured logging
    ├── _run_migrations()        # Alembic upgrade head (subprocess)
    ├── seed()                   # Insert default categories + settings
    └── Ready to serve
```

### Database Session Pattern

```python
# Dependency injection via FastAPI Depends
async def get_db() -> AsyncGenerator[AsyncSession]:
    async with async_session() as session:
        try:
            yield session
            await session.commit()    # Auto-commit on success
        except Exception:
            await session.rollback()  # Auto-rollback on error
            raise
```

### Balance Management

Khi tạo/sửa/xóa giao dịch, balance tài khoản được tự động cập nhật:

| Loại giao dịch | Tài khoản nguồn | Tài khoản đích |
|---|---|---|
| Income | `+amount` | — |
| Expense | `-amount` | — |
| Transfer | `-amount` | `+amount` |

Logic **reverse** balance được áp dụng trước khi update hoặc delete.

---

## Frontend Architecture

### Component Architecture

```
app/
├── layout.tsx              ← Root Layout (font, metadata)
├── providers.tsx           ← QueryClient + Theme + Toast
├── page.tsx                ← Home → Dashboard
└── [module]/page.tsx       ← Thin page wrapper

components/
├── layout/                 ← App shell (Sidebar, Header, FAB)
├── dashboard/              ← Dashboard page + widget components
│   └── components/         ← KPICards, CashFlowChart, SpendingBreakdown...
├── transactions/           ← Transaction pages + drawer
│   └── components/         ← TransactionList, Filters, Pagination, DetailPanel
├── accounts/               ← Account management (inline drawer)
├── budget/                 ← Budget management
├── goals/                  ← Goal tracking + contribute modal
│   └── components/         ← GoalCard, GoalFormDrawer, ContributeModal
├── investments/            ← Investment portfolio
├── recurring/              ← Recurring transaction management
├── reports/                ← Financial reports
│   └── components/         ← Charts, KPIs, CashFlow, PeriodComparison
├── settings/               ← App settings + category management
├── ui/                     ← Reusable UI primitives
└── providers/              ← ThemeProvider
```

### Page Pattern

Mỗi route page là một **thin wrapper** — chỉ import `AppLayout` + feature component:

```tsx
// app/transactions/page.tsx
export default function TransactionsPage() {
  return (
    <AppLayout>
      <TransactionsPage />
    </AppLayout>
  )
}
```

### Routing (App Router)

| Route | Component | Mô tả |
|---|---|---|
| `/` | `Dashboard` | Trang chủ — Tổng quan tài chính |
| `/transactions` | `TransactionsPage` | Danh sách giao dịch |
| `/accounts` | `AccountsPage` | Quản lý tài khoản |
| `/budget` | `BudgetPage` | Ngân sách theo danh mục |
| `/goals` | `GoalsPage` | Mục tiêu tiết kiệm |
| `/investments` | `InvestmentsPage` | Danh mục đầu tư |
| `/recurring` | `RecurringPage` | Giao dịch định kỳ |
| `/reports` | `ReportsPage` | Báo cáo & phân tích |
| `/settings` | `SettingsPage` | Cài đặt ứng dụng |

---

## State Management

### Phân chia trách nhiệm

```
┌────────────────────────────────────────────────────────────┐
│                    TanStack Query v5                        │
│  (Server State — API data cache with auto-refetch)         │
│                                                            │
│  Query Keys:                                               │
│  • ['dashboard', period, month]                            │
│  • ['transactions', ...filters]                            │
│  • ['accounts']                                            │
│  • ['categories', month?]                                  │
│  • ['reports', mode, month, year]                          │
│  • ['goals']                                               │
│  • ['budgets', month]                                      │
│                                                            │
│  Config: staleTime = 30s, refetchOnWindowFocus = false     │
└──────────────────────────┬─────────────────────────────────┘
                           │
┌──────────────────────────▼─────────────────────────────────┐
│                      Zustand v5                             │
│  (Client State — UI state, persisted to localStorage)      │
│                                                            │
│  Persisted:                                                │
│  • sidebarCollapsed (boolean)                              │
│  • theme ('dark' | 'light')                                │
│                                                            │
│  Transient:                                                │
│  • Modal/Drawer open states                                │
│  • Edit IDs (editTransactionId, editAccountId, etc.)       │
│  • Selected items                                          │
│  • Transaction default type                                │
└────────────────────────────────────────────────────────────┘
```

### Custom Hooks

| Hook | Trách nhiệm |
|---|---|
| `useDashboard(period, month)` | Fetch dashboard data + compute KPI diffs |
| `useTransactions()` | Paginated transactions + filters + CRUD + undo |
| `useReports()` | Reports data + month/year navigation |
| `useGoals()` | Goals list query |

---

## Design Patterns

### 1. Thin Page + Fat Component

Route pages chỉ là wrappers. Business logic nằm trong components và hooks.

### 2. Query Invalidation Chain

Khi mutation xảy ra, related queries được invalidated:
```
createTransaction → invalidate [transactions, dashboard, accounts]
deleteTransaction → invalidate [transactions, dashboard, accounts]
createBudget     → invalidate [budgets, dashboard]
```

### 3. Optimistic UI với Undo

Transaction delete sử dụng undo pattern:
1. Xóa ngay trên server
2. Hiển thị toast với nút "Hoàn tác"
3. Nếu undo → re-create transaction
4. Invalidate tất cả related queries

### 4. Async Lock (Backend)

Recurring sync sử dụng `asyncio.Lock()` để đảm bảo chỉ 1 process chạy tại một thời điểm, tránh duplicate transactions.

### 5. Lazy Recurring Sync

Thay vì cron job, recurring transactions được sync **lazily** — khi user truy cập API (`/api/transactions`, `/api/dashboard`, `/api/accounts`).

### 6. CSS Design System

Thay vì sử dụng component library, project dùng CSS Custom Properties (Design Tokens):
- Color palette (dark/light)
- Spacing, Border radius
- Typography (Geist Sans + Instrument Serif)
- Component classes (`.card`, `.btn-*`, `.input`, `.badge-*`, `.kpi-card`)

---

## Error Handling

### Backend
```
Router → catch exceptions
    ├── HTTPException(404) — Resource not found
    ├── HTTPException(400) — Validation error
    └── Auto-rollback session on any exception
```

### Frontend
```
TanStack Query → automatic retry (default 3 times)
    ├── isLoading → Show skeleton/spinner
    ├── isError → Show error state
    └── isSuccess → Render data
```

---

## Security Considerations

> ⚠️ **Single-user app** — Hiện tại không có authentication/authorization.

- CORS giới hạn origins
- Debug mode tắt Swagger Docs trong production
- Database password masked trong logs
- `.env` files excluded từ git
