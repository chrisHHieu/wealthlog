# 🚀 Deployment Guide — WealthLog

## Mục Lục

- [Tổng Quan](#tổng-quan)
- [Docker Compose (Production)](#docker-compose-production)
- [Docker Compose (Development)](#docker-compose-development)
- [Manual Deployment](#manual-deployment)
- [Environment Variables](#environment-variables)
- [Database Management](#database-management)
- [Backup & Restore](#backup--restore)
- [Monitoring & Logging](#monitoring--logging)
- [Troubleshooting](#troubleshooting)
- [Security Checklist](#security-checklist)

---

## Tổng Quan

WealthLog hỗ trợ nhiều cách triển khai:

| Phương pháp | Mô tả | Phù hợp cho |
|---|---|---|
| Docker Compose | One-command deployment, 4 containers | Production, staging |
| Manual | Chạy từng service riêng | Development, debugging |

### Services Architecture

```
docker-compose.yml
├── db          — PostgreSQL 16 Alpine (:5433)
├── backend     — FastAPI + uvicorn (:8001)
├── frontend    — Next.js (SSR) (:3001)
└── db-backup   — Automated daily backups
```

---

## Docker Compose (Production)

### Prerequisites

- Docker Engine ≥ 24.0
- Docker Compose V2

### Quick Start

```bash
# 1. Clone project
git clone <repo-url> wealthlog
cd wealthlog

# 2. (Tùy chọn) Cấu hình environment
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local

# 3. Build & Start
docker compose up -d --build

# 4. Verify
docker compose ps
curl http://localhost:8001/health
```

### Production Configuration

Chỉnh sửa `docker-compose.yml` và `.env` files cho production:

```yaml
# docker-compose.yml adjustments
services:
  backend:
    environment:
      DEBUG: "false"               # Tắt Swagger docs
      CORS_ORIGINS: '["https://yourdomain.com"]'
    restart: always

  frontend:
    build:
      args:
        NEXT_PUBLIC_API_URL: https://api.yourdomain.com
    restart: always
```

### Service Configuration

#### Database (db)

```yaml
services:
  db:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-wealthlog}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-wealthlog2026}
      POSTGRES_DB: wealthlog
    volumes:
      - pgdata:/var/lib/postgresql/data     # Persisted data
    ports:
      - "5433:5432"                         # Host port: 5433
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U wealthlog"]
      interval: 5s
      timeout: 3s
      retries: 5
```

#### Backend

```yaml
services:
  backend:
    build:
      context: ./backend                    # Dockerfile in backend/
    depends_on:
      db:
        condition: service_healthy          # Wait for DB ready
    environment:
      DATABASE_URL: postgresql+asyncpg://...@db:5432/wealthlog
      CORS_ORIGINS: '["http://localhost:3001"]'
      DEBUG: ${DEBUG:-true}
    ports:
      - "8001:8000"
```

**Backend Dockerfile:**
```dockerfile
FROM python:3.13-slim AS base
WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY . .
RUN uv sync --frozen --no-dev
EXPOSE 8000
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### Frontend

```yaml
services:
  frontend:
    build:
      context: ./frontend
    depends_on:
      - backend
    ports:
      - "3001:3000"
```

**Frontend Dockerfile:**
```dockerfile
FROM node:22-alpine AS base
RUN corepack enable && corepack prepare pnpm@latest --activate
WORKDIR /app
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY . .
ARG NEXT_PUBLIC_API_URL=http://localhost:8001
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
RUN pnpm build
EXPOSE 3000
CMD ["pnpm", "start"]
```

#### DB Backup

```yaml
services:
  db-backup:
    image: prodrigestivill/postgres-backup-local
    depends_on:
      db:
        condition: service_healthy
    environment:
      POSTGRES_HOST: db
      POSTGRES_DB: wealthlog
      POSTGRES_USER: ${POSTGRES_USER:-wealthlog}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-wealthlog2026}
      SCHEDULE: "@daily"                    # Backup hàng ngày
      BACKUP_KEEP_DAYS: 7                   # Giữ 7 ngày
      BACKUP_KEEP_WEEKS: 4                  # Giữ 4 tuần
      BACKUP_KEEP_MONTHS: 3                 # Giữ 3 tháng
    volumes:
      - ./backup:/backups                   # Backup files trên host
```

---

## Docker Compose (Development)

Để phát triển với hot-reload, mount source code:

```yaml
# docker-compose.override.yml (tạo file này)
services:
  backend:
    volumes:
      - ./backend/app:/app/app              # Hot-reload Python code
    command: uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

  frontend:
    volumes:
      - ./frontend:/app                     # Hot-reload Next.js
      - /app/node_modules                   # Exclude node_modules
    command: pnpm dev
```

```bash
# Chạy development mode
docker compose up -d
```

---

## Manual Deployment

### 1. Database

```bash
# Cài đặt PostgreSQL 16
# Tạo database
psql -U postgres -c "CREATE USER wealthlog WITH PASSWORD 'wealthlog2026';"
psql -U postgres -c "CREATE DATABASE wealthlog OWNER wealthlog;"
```

### 2. Backend

```bash
cd backend

# Cài đặt uv (nếu chưa có)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Cài đặt dependencies
uv sync

# Tạo .env
cat > .env << EOF
DATABASE_URL=postgresql+asyncpg://wealthlog:wealthlog2026@localhost:5433/wealthlog
CORS_ORIGINS=["http://localhost:3001"]
DEBUG=true
EOF

# Chạy migrations
uv run alembic upgrade head

# Chạy dev server
uv run uvicorn app.main:app --reload --port 8001

# Hoặc production
uv run uvicorn app.main:app --host 0.0.0.0 --port 8001 --workers 4
```

### 3. Frontend

```bash
cd frontend

# Cài đặt pnpm (nếu chưa có)
npm install -g pnpm

# Cài đặt dependencies
pnpm install

# Tạo .env.local
echo "NEXT_PUBLIC_API_URL=http://localhost:8001" > .env.local

# Development
pnpm dev

# Production build
pnpm build
pnpm start
```

---

## Environment Variables

### Backend (`backend/.env`)

| Variable | Required | Default | Mô tả |
|---|---|---|---|
| `DATABASE_URL` | ✅ | `postgresql+asyncpg://wealthlog:wealthlog2026@localhost:5433/wealthlog` | PostgreSQL connection string |
| `DB_POOL_SIZE` | — | `10` | Connection pool size |
| `DB_MAX_OVERFLOW` | — | `20` | Max overflow connections |
| `CORS_ORIGINS` | — | `["http://localhost:3001"]` | Allowed CORS origins (JSON array) |
| `DEBUG` | — | `true` | Enable debug mode + Swagger docs |
| `APP_NAME` | — | `WealthLog API` | Application name |
| `API_PREFIX` | — | `/api` | API route prefix |

### Frontend (`frontend/.env.local`)

| Variable | Required | Default | Mô tả |
|---|---|---|---|
| `NEXT_PUBLIC_API_URL` | ✅ | `""` (empty) | Backend API base URL |

### Docker Compose (root `.env`)

| Variable | Required | Default | Mô tả |
|---|---|---|---|
| `POSTGRES_USER` | — | `wealthlog` | PostgreSQL username |
| `POSTGRES_PASSWORD` | — | `wealthlog2026` | PostgreSQL password |
| `DEBUG` | — | `true` | Backend debug mode |

---

## Database Management

### Migrations

```bash
cd backend

# Xem trạng thái migration hiện tại
uv run alembic current

# Tạo migration mới (autogenerate)
uv run alembic revision --autogenerate -m "description"

# Apply migrations
uv run alembic upgrade head

# Rollback 1 step
uv run alembic downgrade -1

# Rollback to base
uv run alembic downgrade base

# Xem lịch sử migration
uv run alembic history
```

### Auto-Migration on Startup

Backend tự động chạy `alembic upgrade head` khi khởi động (trong `app/main.py`):

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    _run_migrations()        # Always run pending migrations
    await seed(session)      # Seed default data if empty
    yield
```

### Database Seed

Khi database trống, hệ thống tự động seed:
- 18 default categories (thu nhập + chi tiêu + khác)
- 4 default settings (userName, currency, theme, language)

---

## Backup & Restore

### Automated Backups (Docker)

Container `db-backup` tự động backup hàng ngày:
- **Daily:** Giữ 7 ngày gần nhất
- **Weekly:** Giữ 4 tuần gần nhất
- **Monthly:** Giữ 3 tháng gần nhất
- **Location:** `./backup/` directory

### Manual Backup

```bash
# Backup
docker compose exec db pg_dump -U wealthlog wealthlog > backup/manual_$(date +%Y%m%d).sql

# Hoặc không dùng Docker
pg_dump -h localhost -p 5433 -U wealthlog wealthlog > backup.sql
```

### Restore

```bash
# Restore từ backup file
docker compose exec -T db psql -U wealthlog wealthlog < backup/manual_20260416.sql

# Hoặc không dùng Docker
psql -h localhost -p 5433 -U wealthlog wealthlog < backup.sql
```

---

## Monitoring & Logging

### Health Check

```bash
# Backend health
curl http://localhost:8001/health
# → {"status": "ok", "service": "WealthLog API"}

# Database health (Docker)
docker compose exec db pg_isready -U wealthlog
```

### Logs

```bash
# Tất cả services
docker compose logs -f

# Backend only
docker compose logs -f backend

# Frontend only
docker compose logs -f frontend

# Database only
docker compose logs -f db
```

### Backend Log Format

```
2026-04-16 09:30:15 | INFO     | app.main | Starting WealthLog API
2026-04-16 09:30:15 | INFO     | app.main | Debug mode: True
2026-04-16 09:30:16 | INFO     | app.main | Database migrations applied
2026-04-16 09:30:16 | INFO     | app.services.seed | Seed complete: 18 categories, 4 settings
```

---

## Troubleshooting

### Database Connection Error

```
sqlalchemy.exc.OperationalError: connection to server failed
```

**Giải pháp:**
1. Kiểm tra PostgreSQL đang chạy: `docker compose ps db`
2. Kiểm tra port: `docker compose port db 5432`
3. Kiểm tra DATABASE_URL trong `.env`
4. Đợi healthcheck pass: `docker compose exec db pg_isready`

### Frontend Cannot Connect to Backend

```
fetch failed: ERR_CONNECTION_REFUSED
```

**Giải pháp:**
1. Kiểm tra `NEXT_PUBLIC_API_URL` trong `.env.local`
2. Kiểm tra backend đang chạy: `curl http://localhost:8001/health`
3. Kiểm tra CORS_ORIGINS include frontend URL

### Migration Conflict

```
alembic.util.exc.CommandError: Can't locate revision
```

**Giải pháp:**
```bash
# Stamp current state
uv run alembic stamp head

# Re-generate migration
uv run alembic revision --autogenerate -m "fix"
uv run alembic upgrade head
```

### Port Already in Use

```
Error: listen EADDRINUSE :::3001
```

**Giải pháp:**
```bash
# Tìm process đang dùng port
# Windows:
netstat -ano | findstr :3001
taskkill /PID <PID> /F

# Linux/Mac:
lsof -i :3001
kill -9 <PID>
```

### Docker Volume Issues

```bash
# Reset database hoàn toàn
docker compose down -v    # -v = remove volumes
docker compose up -d      # Re-create with fresh database
```

---

## Security Checklist

### Production Deployment

- [ ] Đổi `POSTGRES_PASSWORD` khỏi giá trị mặc định
- [ ] Set `DEBUG=false` để tắt Swagger docs
- [ ] Cấu hình `CORS_ORIGINS` chỉ cho phép domain production
- [ ] Sử dụng HTTPS (reverse proxy: nginx/caddy)
- [ ] Hạn chế port expose (chỉ expose frontend port)
- [ ] Review `.gitignore` — đảm bảo `.env` files không bị push
- [ ] Backup database thường xuyên
- [ ] Monitor logs cho suspicious activity

### Reverse Proxy Example (Nginx)

```nginx
server {
    listen 80;
    server_name wealthlog.example.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name wealthlog.example.com;

    ssl_certificate /etc/ssl/cert.pem;
    ssl_certificate_key /etc/ssl/key.pem;

    # Frontend
    location / {
        proxy_pass http://localhost:3001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Backend API
    location /api/ {
        proxy_pass http://localhost:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Docker Network Isolation

Trong production, chỉ expose frontend port:

```yaml
services:
  db:
    ports: []                    # Không expose database
  backend:
    ports: []                    # Không expose backend trực tiếp
  frontend:
    ports:
      - "3001:3000"             # Chỉ expose frontend
```

Backend được frontend truy cập qua Docker internal network.
