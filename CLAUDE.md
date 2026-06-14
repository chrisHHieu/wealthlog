# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

WealthLog is a full-stack personal finance app for Vietnamese users (UI language: Vietnamese, currency: VND) with an integrated AI financial-advisor agent. Monorepo with two apps:

- `backend/` — FastAPI (async), SQLAlchemy 2.0 + asyncpg, Alembic, Pydantic v2. Package manager: **uv**.
- `frontend/` — Next.js 16 App Router, React 19, TypeScript, Tailwind 4. Package manager: **pnpm**.

## Commands

### Backend (run from `backend/`)

```bash
uv sync --extra dev                                  # install deps incl. test/lint tools
uv run uvicorn app.main:app --reload --port 8001     # dev server (needs Postgres on :5433)

uv run pytest                                        # all tests (no Postgres needed — in-memory SQLite)
uv run pytest -m unit                                # fast pure-function tests
uv run pytest -m integration                         # DB/HTTP API tests
uv run pytest tests/integration/test_transactions.py::test_name   # single test

uv run ruff check .                                  # lint (line-length 100, py312)
uv run ruff format .                                 # format

uv run alembic revision --autogenerate -m "desc"     # new migration (needs Postgres running)
uv run python scripts/run_mcp.py                     # MCP server, stdio mode
uv run python scripts/run_mcp.py --sse               # MCP server, SSE on :8002
```

Migrations are applied **automatically on app startup** (`app/main.py` lifespan runs `alembic upgrade head`, then seeds default data) — you rarely run `alembic upgrade` by hand.

### Frontend (run from `frontend/`)

```bash
pnpm install
pnpm dev          # dev server on :3001 (expects NEXT_PUBLIC_API_URL=http://localhost:8001 in .env.local)
pnpm build
```

There is no frontend lint/test script; type-check with `pnpm exec tsc --noEmit`.

### Docker

```bash
docker compose up -d   # full stack: frontend :3001, backend :8001, Postgres :5433, daily DB backup
```

## Backend Architecture

Layered: **routers** (HTTP) → **schemas** (Pydantic v2 validation) → **services** (business logic) → **models** (SQLAlchemy ORM). Cross-cutting domain logic lives in `app/domain/` (e.g., `balance.py` — account balance updates when transactions change, `resolvers.py`). Configuration is centralized in `app/config.py` (pydantic-settings, env-driven, heavily commented — read it to understand AI tunables).

Finance domain routers (accounts, transactions, budgets, goals, investments, recurring, categories, reports, dashboard, settings) are conventional CRUD; transactions also adjust account balances inside the same DB transaction.

### AI agent subsystem (`app/ai/`)

The most architecturally dense part of the codebase — a Claude-powered chat agent with multi-layer memory:

- **Agent loop** (`ai/agent/runner.py`): ReAct loop streaming SSE events (thinking/text/tool deltas) via the `anthropic` SDK. Tools are the in-process MCP tools in `ai/mcp/tools/` (transactions, reports, budgets, goals, memory, etc.). `ai/agent/compaction.py` implements a 3-tier short-term memory strategy (drop old turns / truncate middle-window tool results / keep recent turns) — tunables in `config.py`.
- **Long-term memory** (`ai/memory/`): user facts with trigram dedup (Postgres-only; SQLite tests fall back to exact match), importance decay + TTL purge (daily background task started in `main.py`), periodic Haiku-driven fact review/consolidation, episodic session summaries with topic-based retrieval, and `UserModel` synthesis on a cadence.
- **Model registry** (`ai/model_registry.py`, `model_catalog.py`): supports Anthropic and DeepSeek providers; the UI model picker shows DeepSeek models only when `DEEPSEEK_API_KEY` is set.
- **MCP server** (`ai/mcp/server.py`): the same tools exposed to external clients (Claude Desktop, MCP Inspector) via `scripts/run_mcp.py`.

Chat persistence/streaming is split across `routers/chat.py`, `chat_streaming.py`, `chat_sessions.py`, `chat_persistence.py`.

### Tests

`tests/conftest.py` builds an in-memory aiosqlite engine, creates tables from ORM metadata (no migrations), and overrides the `get_db` dependency in an httpx `ASGITransport` client — so integration tests exercise the real FastAPI app without Postgres. Be aware some Postgres-only SQL paths (trigram similarity) have SQLite fallbacks; test both behaviors when touching them. `asyncio_mode = auto` — no `@pytest.mark.asyncio` needed.

## Frontend Architecture

- Pages live in `app/(app)/<module>/page.tsx` (dashboard at `app/(app)/page.tsx`); shared shell in `app/(app)/layout.tsx`, providers (QueryClient, theme, toasts) in `app/providers.tsx`.
- **Server state**: TanStack Query via custom hooks in `hooks/` (e.g., `useTransactions.ts`). Mutations invalidate related query keys (a transaction change invalidates transactions + dashboard + accounts).
- **Client/UI state**: single Zustand store at `store/useAppStore.ts`.
- **API layer**: `lib/api.ts` (REST client), `lib/chatStream.ts` + `hooks/useChatState.ts` consume the agent's SSE stream, `lib/chatTimeline.ts` maps stream events to renderable timeline items.
- Components are grouped per feature under `components/<module>/`; reusable primitives (Radix-based) in `components/ui/`; design tokens as CSS variables in `app/globals.css` (dark/light themes).

## Conventions

- Backend code style enforced by Ruff (`E,F,I,N,W,UP`, line 100, first-party = `app`). Structured logging via `app/logging_config.py` with request-ID context — use `get_logger(__name__)`, never `print`.
- Docs in `docs/` (ARCHITECTURE, API, DATABASE, FRONTEND, DEPLOYMENT) are written in Vietnamese and describe the core finance domain; the AI subsystem is newer than some of those docs.
- New ORM models must be imported in `app/models/__init__.py` so Alembic autogenerate and the test-suite `create_all` see them.
