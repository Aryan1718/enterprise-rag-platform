# Server Module (`server/`)

## Purpose

`server/` is the FastAPI backend for Enterprise RAG. It is responsible for:
- Supabase JWT validation
- workspace ownership and isolation checks
- token budget accounting and reservation safety
- API surface for auth/workspace/documents/query/usage
- persistence through SQLAlchemy models over PostgreSQL

Current implementation includes auth/workspace/usage endpoints and token-budget core logic; documents/query/retrieval/chunking/embeddings are scaffolded for next implementation stages.

## FastAPI Structure Breakdown

```text
server/
├── app/
│   ├── main.py               # FastAPI app, CORS, router mounting
│   ├── config.py             # env settings + UTC helpers
│   ├── api/
│   │   ├── auth.py           # GET /auth/me
│   │   ├── workspaces.py     # POST /workspaces, GET /workspaces/me
│   │   ├── usage.py          # GET /usage/today
│   │   ├── documents.py      # scaffold
│   │   └── query.py          # scaffold
│   ├── core/
│   │   ├── auth.py           # JWT validation via Supabase
│   │   ├── token_budget.py   # reserve/release/commit/status
│   │   ├── chunking.py       # scaffold
│   │   ├── embeddings.py     # scaffold
│   │   └── retrieval.py      # scaffold
│   ├── db/
│   │   ├── session.py        # engine/session/base
│   │   └── models.py         # ORM models
│   ├── schemas/              # request/response models
│   └── storage/client.py     # storage scaffold
├── migrations/
└── tests/
```

## Core Modules

### `auth`
- `server/app/core/auth.py`
- Validates bearer JWT against Supabase.
- Primary path: `supabase.auth.get_user(jwt)`.
- Fallback path: direct REST call to `/auth/v1/user` when SDK/httpx compatibility issues occur.

### `token_budget`
- `server/app/core/token_budget.py`
- Implements row-safe daily accounting in `workspace_daily_usage` with lock semantics.
- Handles:
  - `reserve_tokens`
  - `release_tokens`
  - `commit_usage`
  - `get_budget_status`
- Uses upsert-style row initialization (`get_or_create` behavior) for both PostgreSQL and SQLite.

### `database`
- `server/app/db/session.py`: SQLAlchemy engine/session lifecycle.
- `server/app/db/models.py`: ORM for `workspaces`, `documents`, `workspace_daily_usage`.
- Full target schema exists in `scripts/schema.local.sql` and `scripts/schema.supabase.sql`.

### `api routers`
Mounted in `server/app/main.py`:
- `/auth`
- `/workspaces`
- `/documents` (scaffold)
- `/query` (scaffold)
- `/usage`

## How JWT Validation Works

Request path:
1. Client sends `Authorization: Bearer <token>`.
2. `get_current_user` (`app/api/deps.py`) enforces bearer format.
3. `validate_jwt_and_get_user` (`app/core/auth.py`) verifies token with Supabase.
4. On success, request receives `AuthenticatedUser` with `user_id/email/role`.

Minimal check:

```bash
curl -H "Authorization: Bearer <access_token>" \
  http://localhost:8000/auth/me
```

## How Workspace Isolation Works

Isolation model in current implementation:
- `GET /workspaces/me` resolves workspace by `owner_id == current_user.id`.
- `get_workspace_id` dependency returns only the caller-owned workspace id.
- `GET /usage/today` is scoped via that dependency.

Architecture contract requires every data query to include `workspace_id` filters. The current workspace and usage flows follow this; document/query endpoints are pending implementation.

## How Token Reservation Model Works

Core behavior (`app/core/token_budget.py`):

```python
reserve -> tokens_reserved += amount (if within DAILY_TOKEN_LIMIT)
release -> tokens_reserved -= amount
commit  -> tokens_reserved -= amount; tokens_used += amount
status  -> remaining = limit - (used + reserved)
```

Concurrency safety:
- uses transactional row locks (`SELECT ... FOR UPDATE` where supported)
- tested for reservation race behavior in `server/tests/test_token_budget.py`

Example usage endpoint:

```bash
curl -H "Authorization: Bearer <access_token>" \
  http://localhost:8000/usage/today
```

## Important Environment Variables

From `server/.env.example` and `app/config.py`:

```bash
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
SUPABASE_KEY=                 # optional alias
DATABASE_URL=
REDIS_URL=
ENVIRONMENT=development
API_HOST=0.0.0.0
API_PORT=8000
DAILY_TOKEN_LIMIT=100000
RESERVATION_TTL_SECONDS=600
```

Notes:
- `SUPABASE_SERVICE_ROLE_KEY` is preferred; `SUPABASE_KEY` is accepted as fallback.
- `RESERVATION_TTL_SECONDS` is used by maintenance cleanup logic (currently in worker).

## How To Run Server

### Local Python

```bash
cd server
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Docker Compose

```bash
docker-compose up server
```

Health check:

```bash
curl http://localhost:8000/health
```

## Future Expansion Notes

Planned next backend milestones (aligned with locked architecture):
- implement document upload lifecycle and metadata validation
- add extraction/chunking/embedding orchestration endpoints
- implement pgvector retrieval and grounded `/query`
- add workspace-scoped rate limiting and structured logging
- complete repository layer under `app/db/repositories/`
- expand Alembic migrations and integration tests beyond health/token-budget
