# Worker Module (`worker/`)

## Purpose of Worker Service

`worker/` runs asynchronous background jobs for ingestion and operational maintenance. It is designed to decouple long-running PDF processing/indexing tasks from synchronous API requests.

Current state:
- queue runner is implemented (`worker.py`)
- ingestion jobs are scaffolded stubs
- stale token reservation cleanup logic is implemented (`jobs/maintenance.py`)

## RQ Queue Architecture

`worker/worker.py`:
- reads `QUEUE_NAME` (or CLI arg) and `REDIS_URL`
- creates Redis connection
- creates RQ `Queue`
- starts `Worker([queue])`

Queue names used by compose:
- `ingest_extract`
- `ingest_index`

Example startup:

```bash
cd worker
QUEUE_NAME=ingest_extract REDIS_URL=redis://localhost:6379/0 python worker.py
```

## `ingest_extract` vs `ingest_index`

### `jobs/ingest_extract.py`
Intended responsibility (locked architecture):
- fetch uploaded PDF metadata/blob
- extract page text
- persist `document_pages`
- update document state (`uploaded` -> `indexing` or `failed`)

Current status:
- placeholder `run(document_id: str)` function

### `jobs/ingest_index.py`
Intended responsibility (locked architecture):
- chunk extracted page text
- generate embeddings
- persist `chunks` and `chunk_embeddings`
- mark document `ready` when complete

Current status:
- placeholder `run(document_id: str)` function

## Maintenance Jobs (Token Cleanup)

`jobs/maintenance.py` implements `cleanup_stale_reservations()`:
- connects to DB via `DATABASE_URL`
- reads `RESERVATION_TTL_SECONDS` (default `600`)
- sets `tokens_reserved=0` for stale rows in `workspace_daily_usage`
- supports PostgreSQL and SQLite SQL variants

Example invocation:

```bash
cd worker
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/enterprise_rag \
RESERVATION_TTL_SECONDS=600 \
python -c "from jobs.maintenance import cleanup_stale_reservations; print(cleanup_stale_reservations())"
```

## How Redis Integrates

Redis is both:
- transport for queued jobs
- worker coordination backend for RQ

In `docker-compose.yml`:
- Redis service runs at `redis://redis:6379/0` inside containers
- workers and server share that connection target for enqueue/consume workflows

## How To Start Worker

### Local Python

```bash
cd worker
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
QUEUE_NAME=ingest_extract REDIS_URL=redis://localhost:6379/0 python worker.py
```

Run index worker:

```bash
QUEUE_NAME=ingest_index REDIS_URL=redis://localhost:6379/0 python worker.py
```

### Docker Compose

```bash
docker-compose up worker-extract worker-index
```

## Scaling Workers

Current compose defaults:
- `worker-extract` replicas: `5`
- `worker-index` replicas: `3`

Scaling options:
- increase replicas in compose/orchestrator
- split queue responsibilities by workload
- tune queue depth monitoring via RQ Dashboard (`:9181`)

Recommended operational pattern:
- keep extract workers higher than index if extraction is I/O-bound
- keep index workers sized for embedding throughput and API rate limits

## Failure Handling

Expected model per locked architecture:
- job exceptions move document to `failed`
- retry transient failures with bounded retries/backoff
- keep idempotency by document/chunk hashes
- log structured context for postmortems

Current implemented behavior:
- RQ worker loop is active
- ingestion retry/error transitions are not yet implemented in job stubs
- maintenance cleanup function returns affected row count for observability

## Shared Code Integration

`worker/shared/` is intended to mirror/reuse server logic (models/config/core) to avoid divergence.

Current repo state:
- shared package is present as placeholder
- compose mounts `./server/app` into `/app/shared` for practical code sharing during development
