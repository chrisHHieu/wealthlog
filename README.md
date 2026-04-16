# 💎 WealthLog — Quản Lý Tài Chính Cá Nhân

<p align="center">
  <img src="https://img.shields.io/badge/Frontend-Next.js_16-000000?style=for-the-badge&logo=nextdotjs" alt="Next.js"/>
  <img src="https://img.shields.io/badge/Backend-FastAPI-009688?style=for-the-badge&logo=fastapi" alt="FastAPI"/>
  <img src="https://img.shields.io/badge/Database-PostgreSQL_16-4169E1?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL"/>
  <img src="https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker"/>
</p>

> Ứng dụng quản lý tài chính cá nhân **full-stack** với giao diện Luxury Fintech, hỗ trợ theo dõi chi tiêu, ngân sách, mục tiêu tiết kiệm, đầu tư và phân tích tài chính theo quy tắc 50/30/20.

---

## 📋 Mục Lục

- [Tổng Quan](#-tổng-quan)
- [Tính Năng](#-tính-năng)
- [Kiến Trúc](#-kiến-trúc)
- [Tech Stack](#-tech-stack)
- [Cài Đặt & Khởi Chạy](#-cài-đặt--khởi-chạy)
- [Cấu Trúc Thư Mục](#-cấu-trúc-thư-mục)
- [Tài Liệu Chi Tiết](#-tài-liệu-chi-tiết)

---

## 🌟 Tổng Quan

**WealthLog** là ứng dụng quản lý tài chính cá nhân được thiết kế dành riêng cho người dùng Việt Nam, với:

- Giao diện **Luxury Fintech** — Dark/Light mode, glassmorphism, micro-animations
- Backend **async** hiệu năng cao với FastAPI + SQLAlchemy 2.0
- Database **PostgreSQL 16** với auto-migration qua Alembic
- Deploy dễ dàng bằng **Docker Compose** (one-command setup)
- Ngôn ngữ giao diện: **Tiếng Việt**, đơn vị tiền tệ: **VND**

---

## ✨ Tính Năng

### Quản Lý Giao Dịch
- ✅ Thu nhập / Chi tiêu / Chuyển khoản
- ✅ Tìm kiếm, lọc theo loại, tài khoản, danh mục, tháng
- ✅ Phân trang server-side
- ✅ Undo xóa giao dịch (toast undo)
- ✅ Tự động cập nhật số dư tài khoản

### Dashboard Tổng Quan
- ✅ Net Worth (tổng tài sản ròng)
- ✅ KPI cards: Thu nhập, Chi tiêu, Tiết kiệm (so sánh tháng trước)
- ✅ Biểu đồ dòng tiền hàng tháng (3/6/12 tháng)
- ✅ Phân tích chi tiêu theo danh mục (Pie chart)
- ✅ Quy tắc 50/30/20 (Needs/Wants/Savings)
- ✅ Tiến độ ngân sách, mục tiêu tiết kiệm
- ✅ Hóa đơn sắp đến hạn, giao dịch gần đây
- ✅ Tổng quan tài sản & nợ

### Tài Khoản
- ✅ 6 loại: Tiền mặt, Ngân hàng, Ví điện tử, Đầu tư, Tiết kiệm, Nợ vay
- ✅ Tùy chỉnh icon, màu sắc
- ✅ Tự động cập nhật balance theo giao dịch

### Ngân Sách
- ✅ Thiết lập ngân sách theo danh mục & tháng
- ✅ Cảnh báo khi chi tiêu > 80% hoặc vượt ngân sách
- ✅ Kiểm tra ngân sách real-time khi tạo giao dịch

### Mục Tiêu Tiết Kiệm
- ✅ 6 loại: Khẩn cấp, Tiết kiệm, Mua sắm, Đầu tư, Trả nợ, Tùy chỉnh
- ✅ Đóng góp tiền, theo dõi tiến độ
- ✅ Tính toán số tiền cần tiết kiệm mỗi tháng

### Đầu Tư
- ✅ 7 loại: Cổ phiếu, ETF, Vàng, Bất động sản, Tiết kiệm, Crypto, Khác
- ✅ Theo dõi lãi/lỗ, giá mua vs giá hiện tại

### Giao Dịch Định Kỳ
- ✅ Tần suất: Hàng ngày, Hàng tuần, Hàng tháng, Hàng năm
- ✅ Tùy chọn ngày trong tuần (cho weekly)
- ✅ Tự động tạo giao dịch khi đến hạn
- ✅ Bật/tắt trạng thái

### Báo Cáo & Phân Tích
- ✅ Chế độ xem: Theo tháng / Theo năm
- ✅ So sánh với kỳ trước (thu nhập, chi tiêu, tiết kiệm)
- ✅ Biểu đồ thu nhập - chi tiêu
- ✅ Xu hướng chi tiêu tích lũy
- ✅ So sánh danh mục chi tiêu / thu nhập
- ✅ Cash Flow Statement
- ✅ Top 5 giao dịch lớn nhất

### Cài Đặt
- ✅ Dark / Light mode
- ✅ Quản lý danh mục (tạo, sửa, phân nhóm 50/30/20)
- ✅ Xuất dữ liệu CSV/Excel
- ✅ Thông tin người dùng

---

## 🏗 Kiến Trúc

```
┌─────────────────────────────────────────────────────────────┐
│                        Docker Compose                       │
├──────────────┬────────────────┬──────────────┬──────────────┤
│   Frontend   │    Backend     │  PostgreSQL  │  DB Backup   │
│  Next.js 16  │   FastAPI      │     16       │   (daily)    │
│  :3001       │   :8001        │   :5433      │              │
│              │                │              │              │
│  React 19    │  SQLAlchemy 2  │  pgdata vol  │  7d/4w/3m    │
│  TanStack Q  │  Alembic       │              │              │
│  Zustand     │  Pydantic v2   │              │              │
│  Recharts    │  asyncpg       │              │              │
│  Tailwind 4  │  uv            │              │              │
└──────────────┴────────────────┴──────────────┴──────────────┘
```

---

## 🛠 Tech Stack

### Frontend
| Công nghệ | Phiên bản | Mục đích |
|---|---|---|
| Next.js | 16.2 | React Framework (App Router) |
| React | 19.2 | UI Library |
| TypeScript | 5.x | Type Safety |
| Tailwind CSS | 4.x | Utility-first CSS |
| TanStack Query | 5.x | Server State Management |
| Zustand | 5.x | Client State Management |
| Recharts | 3.x | Data Visualization |
| React Hook Form + Zod | 7.x / 4.x | Form Validation |
| Framer Motion | 12.x | Animations |
| Radix UI | latest | Accessible Primitives |
| Lucide React | 1.x | Icon System |
| ExcelJS + PapaParse | — | CSV/Excel Export |

### Backend
| Công nghệ | Phiên bản | Mục đích |
|---|---|---|
| Python | ≥ 3.12 | Runtime |
| FastAPI | ≥ 0.115 | Web Framework |
| SQLAlchemy | ≥ 2.0 (async) | ORM |
| asyncpg | ≥ 0.30 | PostgreSQL Driver |
| Alembic | ≥ 1.14 | Database Migrations |
| Pydantic | ≥ 2.10 | Schema Validation |
| pydantic-settings | ≥ 2.7 | Configuration |
| python-dateutil | ≥ 2.9 | Date Utilities |
| uv | latest | Package Manager |
| Ruff | ≥ 0.8 | Linter/Formatter |

### Infrastructure
| Công nghệ | Mục đích |
|---|---|
| PostgreSQL 16 Alpine | Database |
| Docker + Docker Compose | Containerization |
| postgres-backup-local | Automated Backups (7d/4w/3m) |

---

## 🚀 Cài Đặt & Khởi Chạy

### Yêu Cầu
- **Docker** + Docker Compose (khuyến nghị)
- Hoặc: Node.js ≥ 22, Python ≥ 3.12, PostgreSQL 16

### Cách 1: Docker Compose (Khuyến nghị)

```bash
# Clone project
git clone <repo-url> wealthlog
cd wealthlog

# Tạo file .env (tùy chọn, đã có giá trị mặc định)
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local

# Khởi chạy toàn bộ stack
docker compose up -d

# Truy cập:
# Frontend: http://localhost:3001
# Backend API: http://localhost:8001
# Swagger Docs: http://localhost:8001/docs
```

### Cách 2: Development Mode (Local)

**Backend:**
```bash
cd backend

# Cài đặt dependencies với uv
uv sync

# Khởi động PostgreSQL (cần chạy sẵn ở port 5433)
# Tạo database 'wealthlog' nếu chưa có

# Chạy dev server
uv run uvicorn app.main:app --reload --port 8001
```

**Frontend:**
```bash
cd frontend

# Cài đặt dependencies
pnpm install

# Tạo .env.local
echo "NEXT_PUBLIC_API_URL=http://localhost:8001" > .env.local

# Chạy dev server
pnpm dev
# → http://localhost:3001
```

### Biến Môi Trường

| Biến | Mặc định | Mô tả |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://wealthlog:wealthlog2026@localhost:5433/wealthlog` | Connection string PostgreSQL |
| `CORS_ORIGINS` | `["http://localhost:3001"]` | Allowed CORS origins |
| `DEBUG` | `true` | Bật/tắt debug mode (Swagger Docs) |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8001` | Backend API URL cho frontend |
| `POSTGRES_USER` | `wealthlog` | PostgreSQL username |
| `POSTGRES_PASSWORD` | `wealthlog2026` | PostgreSQL password |

---

## 📁 Cấu Trúc Thư Mục

```
wealthlog/
├── docker-compose.yml          # Docker orchestration
├── .gitignore
│
├── backend/                    # FastAPI Backend
│   ├── Dockerfile
│   ├── pyproject.toml          # Dependencies (uv)
│   ├── alembic.ini             # Migration config
│   ├── alembic/                # Database migrations
│   │   └── versions/           # Migration scripts
│   ├── app/
│   │   ├── main.py             # FastAPI entrypoint
│   │   ├── config.py           # Settings (pydantic-settings)
│   │   ├── database.py         # SQLAlchemy engine + session
│   │   ├── logging_config.py   # Structured logging
│   │   ├── models/             # SQLAlchemy ORM models
│   │   ├── schemas/            # Pydantic v2 schemas
│   │   ├── routers/            # API route handlers
│   │   ├── services/           # Business logic
│   │   └── utils/              # Shared utilities
│   └── tests/                  # Pytest test suite
│
├── frontend/                   # Next.js Frontend
│   ├── Dockerfile
│   ├── package.json            # Dependencies (pnpm)
│   ├── app/                    # Next.js App Router pages
│   │   ├── layout.tsx          # Root layout
│   │   ├── page.tsx            # Home → Dashboard
│   │   ├── globals.css         # Design system (CSS vars)
│   │   ├── providers.tsx       # QueryClient + Theme + Toast
│   │   └── [module]/page.tsx   # Feature pages
│   ├── components/             # React components
│   │   ├── dashboard/          # Dashboard widget components
│   │   ├── transactions/       # Transaction list + drawer
│   │   ├── accounts/           # Account management
│   │   ├── budget/             # Budget management
│   │   ├── goals/              # Goal tracking
│   │   ├── investments/        # Investment portfolio
│   │   ├── recurring/          # Recurring transactions
│   │   ├── reports/            # Reports & analytics
│   │   ├── settings/           # App settings
│   │   ├── layout/             # Sidebar, Header, FAB
│   │   ├── ui/                 # Reusable UI primitives
│   │   └── providers/          # Theme provider
│   ├── hooks/                  # Custom React hooks
│   ├── lib/                    # Utilities, API config, validations
│   ├── store/                  # Zustand global store
│   └── types/                  # TypeScript interfaces
│
└── backup/                     # Auto-generated DB backups
```

---

## 📖 Tài Liệu Chi Tiết

| Tài liệu | Mô tả |
|---|---|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Kiến trúc tổng thể, design patterns, luồng dữ liệu |
| [docs/API.md](docs/API.md) | API Reference — tất cả endpoints, request/response schemas |
| [docs/DATABASE.md](docs/DATABASE.md) | Database schema, ERD, relationships, migrations |
| [docs/FRONTEND.md](docs/FRONTEND.md) | Frontend architecture, component tree, state management |
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) | Hướng dẫn deploy Docker, production config |

---

## 📜 License

Private Project — All Rights Reserved.

---

<p align="center">
  <sub>Built with ❤️ for personal finance management</sub>
</p>
