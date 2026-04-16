# 📡 API Reference — WealthLog

> Base URL: `http://localhost:8001`  
> Tất cả endpoints có prefix `/api/`  
> Content-Type: `application/json`

---

## Mục Lục

- [Health Check](#health-check)
- [Accounts](#accounts)
- [Categories](#categories)
- [Transactions](#transactions)
- [Budgets](#budgets)
- [Goals](#goals)
- [Investments](#investments)
- [Recurring Transactions](#recurring-transactions)
- [Dashboard](#dashboard)
- [Reports](#reports)
- [Settings](#settings)

---

## Health Check

### `GET /health`

Kiểm tra trạng thái server.

**Response:**
```json
{
  "status": "ok",
  "service": "WealthLog API"
}
```

---

## Accounts

### `GET /api/accounts`

Lấy danh sách tất cả tài khoản.

> ⚡ Trigger recurring sync trước khi trả kết quả.

**Response:** `AccountResponse[]`
```json
[
  {
    "id": "uuid",
    "name": "VCB Checking",
    "type": "bank",           // cash | bank | ewallet | investment | savings | debt
    "balance": 15000000,
    "currency": "VND",
    "color": "#00C896",
    "icon": "💳",
    "description": null,
    "isActive": true,
    "createdAt": "2026-04-01T...",
    "updatedAt": "2026-04-01T..."
  }
]
```

### `POST /api/accounts`

Tạo tài khoản mới.

**Request Body:** `AccountCreate`
```json
{
  "name": "Ví MoMo",
  "type": "ewallet",
  "balance": 500000,
  "color": "#ec4899",
  "icon": "📱",
  "description": "Ví điện tử MoMo"
}
```

**Response:** `201` — `AccountResponse`

### `GET /api/accounts/{account_id}`

Lấy thông tin chi tiết tài khoản.

**Response:** `AccountResponse` | `404`

### `PUT /api/accounts/{account_id}`

Cập nhật tài khoản. Chấp nhận partial update.

**Request Body:** `AccountUpdate` (tất cả fields optional)
```json
{
  "name": "VCB Savings",
  "balance": 20000000
}
```

**Response:** `AccountResponse` | `404`

### `DELETE /api/accounts/{account_id}`

Xóa tài khoản. Tự động nullify `toAccountId` trên các giao dịch transfer liên quan.

**Response:**
```json
{ "success": true }
```

---

## Categories

### `GET /api/categories`

Lấy danh sách danh mục.

**Query Parameters:**

| Param | Type | Mô tả |
|---|---|---|
| `usedOnly` | boolean | Chỉ lấy danh mục đã được dùng trong giao dịch |
| `startDate` | string | Filter giao dịch từ ngày (YYYY-MM-DD) |
| `endDate` | string | Filter giao dịch đến ngày (YYYY-MM-DD) |

**Response:** `CategoryResponse[]`
```json
[
  {
    "id": "uuid",
    "name": "Ăn uống",
    "type": "expense",          // income | expense | both
    "budgetGroup": "needs",     // needs | wants | savings | null
    "icon": "🍜",
    "color": "#f59e0b",
    "isDefault": true,
    "createdAt": "2026-04-01T..."
  }
]
```

### `POST /api/categories`

Tạo danh mục mới.

**Request Body:** `CategoryCreate`
```json
{
  "name": "Thú cưng",
  "type": "expense",
  "icon": "🐾",
  "color": "#8b5cf6"
}
```

### `PUT /api/categories?id={category_id}`

Cập nhật danh mục. ID qua query parameter.

**Request Body:** `CategoryUpdate`
```json
{
  "name": "Thú cưng & Pets",
  "budgetGroup": "wants"
}
```

### `DELETE /api/categories?id={category_id}`

Xóa danh mục.

---

## Transactions

### `GET /api/transactions`

Lấy danh sách giao dịch. Hỗ trợ 2 chế độ:
- **Paginated mode** (khi có `page`): Trả về `PaginatedResponse`
- **Legacy array mode** (không có `page`): Trả về `TransactionResponse[]`

> ⚡ Trigger recurring sync trước khi trả kết quả.

**Query Parameters:**

| Param | Type | Default | Mô tả |
|---|---|---|---|
| `page` | int | — | Số trang (bắt đầu từ 1) |
| `pageSize` | int | 50 | Số item mỗi trang |
| `limit` | int | 200 | Giới hạn (legacy mode) |
| `startDate` | string | — | Từ ngày (YYYY-MM-DD) |
| `endDate` | string | — | Đến ngày (YYYY-MM-DD) |
| `accountId` | UUID | — | Filter theo tài khoản |
| `categoryId` | UUID | — | Filter theo danh mục |
| `type` | string | — | `income` / `expense` / `transfer` |
| `search` | string | — | Tìm kiếm trong `description` |

**Response (Paginated):**
```json
{
  "data": [
    {
      "id": "uuid",
      "type": "expense",
      "amount": 150000,
      "accountId": "uuid",
      "toAccountId": null,
      "categoryId": "uuid",
      "description": "Cà phê sáng",
      "note": null,
      "tags": null,
      "date": "2026-04-16",
      "accountName": "VCB Checking",
      "accountIcon": "💳",
      "categoryName": "Ăn uống",
      "categoryIcon": "🍜",
      "categoryColor": "#f59e0b",
      "createdAt": "...",
      "updatedAt": "..."
    }
  ],
  "total": 150,
  "page": 1,
  "pageSize": 50,
  "totalPages": 3
}
```

### `POST /api/transactions`

Tạo giao dịch mới. Tự động cập nhật balance tài khoản.

**Request Body:** `TransactionCreate`
```json
{
  "type": "expense",
  "amount": 150000,
  "accountId": "uuid",
  "toAccountId": null,
  "categoryId": "uuid",
  "description": "Cà phê sáng",
  "note": "Highland Coffee",
  "tags": ["cafe"],
  "date": "2026-04-16"
}
```

**Response:** `201` — `TransactionResponse`

### `GET /api/transactions/{transaction_id}`

**Response:** `TransactionResponse` | `404`

### `PUT /api/transactions/{transaction_id}`

Cập nhật giao dịch. Tự động reverse balance cũ → apply balance mới.

**Request Body:** `TransactionUpdate` (partial)

### `DELETE /api/transactions/{transaction_id}`

Xóa giao dịch. Tự động reverse balance.

**Response:**
```json
{ "success": true }
```

---

## Budgets

### `GET /api/budgets`

Lấy danh sách ngân sách theo tháng.

**Query Parameters:**

| Param | Type | Default | Mô tả |
|---|---|---|---|
| `month` | string | Current month | Tháng (YYYY-MM) |

**Response:** `BudgetResponse[]`
```json
[
  {
    "id": "uuid",
    "categoryId": "uuid",
    "amount": 3000000,
    "month": "2026-04",
    "categoryName": "Ăn uống",
    "categoryIcon": "🍜",
    "categoryColor": "#f59e0b",
    "createdAt": "..."
  }
]
```

### `POST /api/budgets`

Tạo/cập nhật ngân sách. **Upsert behavior** — nếu đã tồn tại budget cho cùng `categoryId + month`, sẽ thay thế.

**Request Body:** `BudgetCreate`
```json
{
  "categoryId": "uuid",
  "amount": 3000000,
  "month": "2026-04"
}
```

### `DELETE /api/budgets?id={budget_id}`

Xóa ngân sách.

### `GET /api/budgets/check`

Kiểm tra trạng thái ngân sách cho một danh mục.

**Query Parameters:**

| Param | Type | Mô tả |
|---|---|---|
| `categoryId` | UUID | **Required** — ID danh mục |
| `month` | string | Tháng (YYYY-MM), mặc định tháng hiện tại |

**Response:** `BudgetCheckResponse | null`
```json
{
  "budgetAmount": 3000000,
  "totalSpent": 2500000,
  "percent": 83,
  "remaining": 500000,
  "isExceeded": false,
  "isWarning": true
}
```

---

## Goals

### `GET /api/goals`

Lấy danh sách mục tiêu, kèm contributions.

**Response:** `GoalResponse[]`
```json
[
  {
    "id": "uuid",
    "name": "Quỹ khẩn cấp",
    "type": "emergency",
    "targetAmount": 50000000,
    "currentAmount": 15000000,
    "deadline": "2026-12-31",
    "icon": "🎯",
    "color": "#00C896",
    "description": "6 tháng chi tiêu",
    "isCompleted": false,
    "contributions": [
      {
        "id": "uuid",
        "goalId": "uuid",
        "amount": 5000000,
        "note": "Lương tháng 4",
        "date": "2026-04-01",
        "createdAt": "..."
      }
    ],
    "createdAt": "...",
    "updatedAt": "..."
  }
]
```

### `POST /api/goals`

Tạo mục tiêu mới.

**Request Body:** `GoalCreate`
```json
{
  "name": "Macbook Pro",
  "type": "purchase",
  "targetAmount": 40000000,
  "currentAmount": 0,
  "deadline": "2026-12-31",
  "icon": "💻",
  "color": "#3b82f6",
  "description": "Macbook Pro M4"
}
```

### `GET /api/goals/{goal_id}`

### `PUT /api/goals/{goal_id}`

### `POST /api/goals/{goal_id}/contribute`

Thêm đóng góp vào mục tiêu. Tự động cập nhật `currentAmount` và đánh dấu `isCompleted` nếu đã đạt.

**Request Body:** `GoalAddAmount`
```json
{
  "amount": 5000000,
  "note": "Tiết kiệm tháng 4",
  "date": "2026-04-15"
}
```

### `DELETE /api/goals/{goal_id}`

---

## Investments

### `GET /api/investments`

Lấy danh sách đầu tư, sắp xếp theo `buyDate`.

**Response:** `InvestmentResponse[]`
```json
[
  {
    "id": "uuid",
    "name": "VNM",
    "type": "stock",
    "symbol": "VNM",
    "quantity": 100,
    "buyPrice": 75000,
    "currentPrice": 82000,
    "buyDate": "2026-01-15",
    "accountId": "uuid",
    "note": "Vinamilk",
    "createdAt": "...",
    "updatedAt": "..."
  }
]
```

### `POST /api/investments`

**Request Body:** `InvestmentCreate`
```json
{
  "name": "VNM",
  "type": "stock",
  "symbol": "VNM",
  "quantity": 100,
  "buyPrice": 75000,
  "currentPrice": 82000,
  "buyDate": "2026-01-15",
  "accountId": "uuid",
  "note": "Vinamilk"
}
```

### `PUT /api/investments/{investment_id}`

### `DELETE /api/investments/{investment_id}`

---

## Recurring Transactions

### `GET /api/recurring`

Lấy danh sách giao dịch định kỳ.

> ⚡ Trigger recurring sync trước khi trả kết quả.

**Response:** `RecurringResponse[]`
```json
[
  {
    "id": "uuid",
    "type": "expense",
    "amount": 5000000,
    "accountId": "uuid",
    "toAccountId": null,
    "categoryId": "uuid",
    "description": "Tiền nhà",
    "frequency": "monthly",
    "daysOfWeek": null,
    "startDate": "2026-01-01",
    "nextRunDate": "2026-05-01",
    "lastRunDate": "2026-04-01T...",
    "isActive": true,
    "accountName": "VCB Checking",
    "categoryName": "Nhà ở",
    "categoryIcon": "🏠",
    "categoryColor": "#14b8a6",
    "createdAt": "..."
  }
]
```

### `POST /api/recurring`

**Request Body:** `RecurringCreate`
```json
{
  "type": "expense",
  "amount": 5000000,
  "accountId": "uuid",
  "categoryId": "uuid",
  "description": "Tiền nhà",
  "frequency": "monthly",
  "daysOfWeek": null,
  "startDate": "2026-01-01",
  "nextRunDate": "2026-05-01"
}
```

### `PUT /api/recurring/{item_id}`

### `PATCH /api/recurring/{item_id}`

Partial update (cùng logic với PUT).

### `DELETE /api/recurring/{item_id}`

---

## Dashboard

### `GET /api/dashboard`

Endpoint aggregation trả về toàn bộ dữ liệu cho trang Dashboard.

> ⚡ Trigger recurring sync trước khi tính toán.

**Query Parameters:**

| Param | Type | Default | Mô tả |
|---|---|---|---|
| `period` | string | `6months` | `3months` / `6months` / `12months` |
| `month` | string | Current month | Tháng được chọn (YYYY-MM) |

**Response:** `DashboardData`
```json
{
  "netWorth": 150000000,
  "selectedMonth": "2026-04",

  "currentMonth": {
    "income": 25000000,
    "expense": 18000000,
    "savings": 7000000
  },

  "previousMonth": {
    "income": 23000000,
    "expense": 16000000,
    "savings": 7000000
  },

  "monthlyChart": [
    { "month": "2025-11", "income": 22000000, "expense": 15000000 },
    { "month": "2025-12", "income": 24000000, "expense": 17000000 }
  ],

  "categoryBreakdown": [
    {
      "categoryId": "uuid",
      "categoryName": "Ăn uống",
      "categoryIcon": "🍜",
      "categoryColor": "#f59e0b",
      "budgetGroup": "needs",
      "total": 5000000
    }
  ],

  "spendingByGroup": {
    "needs": 10000000,
    "wants": 5000000,
    "savings": 7000000,
    "unassigned": 3000000
  },

  "recentTransactions": [
    {
      "id": "uuid",
      "type": "expense",
      "amount": 150000,
      "description": "Cà phê sáng",
      "date": "2026-04-16",
      "categoryName": "Ăn uống",
      "categoryIcon": "🍜",
      "categoryColor": "#f59e0b"
    }
  ],

  "budgetProgress": [
    {
      "categoryId": "uuid",
      "categoryName": "Ăn uống",
      "categoryIcon": "🍜",
      "categoryColor": "#f59e0b",
      "budgetAmount": 3000000,
      "spentAmount": 2500000
    }
  ],

  "upcomingBills": [
    {
      "id": "uuid",
      "description": "Tiền nhà",
      "amount": 5000000,
      "type": "expense",
      "nextRunDate": "2026-05-01",
      "frequency": "monthly",
      "categoryIcon": "🏠",
      "categoryColor": "#14b8a6"
    }
  ],

  "assetLiability": {
    "assets": [
      { "type": "bank", "label": "Ngân hàng", "total": 100000000 },
      { "type": "savings", "label": "Tiết kiệm", "total": 50000000 }
    ],
    "liabilities": [
      { "type": "debt", "label": "Nợ vay", "total": 20000000 }
    ],
    "totalAssets": 150000000,
    "totalLiabilities": 20000000
  }
}
```

---

## Reports

### `GET /api/reports`

Endpoint aggregation cho trang báo cáo.

**Query Parameters:**

| Param | Type | Default | Mô tả |
|---|---|---|---|
| `mode` | string | `month` | `month` / `year` |
| `month` | string | Current month | Tháng (YYYY-MM) — dùng khi mode=month |
| `year` | string | Current year | Năm — dùng khi mode=year |

**Response:** `ReportsData`
```json
{
  "current": {
    "income": 25000000,
    "expense": 18000000,
    "savings": 7000000,
    "savingsRate": 28.0
  },

  "previous": {
    "income": 23000000,
    "expense": 16000000,
    "savings": 7000000,
    "savingsRate": 30.4
  },

  "chartData": [
    { "label": "1", "income": 0, "expense": 150000 },
    { "label": "2", "income": 25000000, "expense": 500000 }
  ],

  "trendData": [
    { "label": "1", "cumExpense": 150000, "expense": 150000 },
    { "label": "2", "cumExpense": 650000, "expense": 500000 }
  ],

  "expenseByCategory": [
    {
      "categoryId": "uuid",
      "name": "Ăn uống",
      "icon": "🍜",
      "color": "#f59e0b",
      "current": 5000000,
      "previous": 4500000,
      "pct": 27.8
    }
  ],

  "incomeByCategory": [ ... ],

  "cashFlow": {
    "incomeItems": [ ... ],
    "expenseItems": [ ... ],
    "totalIncome": 25000000,
    "totalExpense": 18000000,
    "net": 7000000
  },

  "topTransactions": [
    {
      "type": "expense",
      "amount": 5000000,
      "date": "2026-04-01",
      "categoryName": "Nhà ở",
      "categoryIcon": "🏠",
      "categoryColor": "#14b8a6"
    }
  ]
}
```

---

## Settings

### `GET /api/settings`

Lấy tất cả settings dưới dạng key-value map.

**Response:**
```json
{
  "data": {
    "userName": "Nguyễn Hoàng Hiếu",
    "currency": "VND",
    "theme": "dark",
    "language": "vi"
  }
}
```

### `PUT /api/settings`

Cập nhật settings. **Upsert behavior** — tạo mới nếu key chưa tồn tại.

**Request Body:**
```json
{
  "data": {
    "userName": "Nguyễn Văn A",
    "theme": "light"
  }
}
```

**Response:**
```json
{ "success": true }
```

---

## Mã Lỗi

| Code | Ý nghĩa |
|---|---|
| `200` | Thành công |
| `201` | Tạo mới thành công |
| `404` | Không tìm thấy resource |
| `422` | Validation error (Pydantic) |
| `500` | Internal server error |

---

## Swagger Docs

Khi `DEBUG=true`, Swagger UI có sẵn tại:
- **Swagger UI:** `http://localhost:8001/docs`
- **ReDoc:** `http://localhost:8001/redoc`
