# Client (`client/`)

Frontend for Enterprise RAG v1 using React + Vite + TypeScript + Tailwind.

## Implemented UI/UX Scope

- Auth: `/login`, `/signup`
- Workspace creation gate: `/workspace`
- Protected app shell with persistent sidebar + top bar: `/app/*`
- Upload and ingestion tracking: `/app/upload`
  - Includes per-row `Delete` action (calls `DELETE /documents/{id}`)
- Document-context chat scaffold (stubbed reply): `/app/chat`
- Separate workspace info page: `/app/workspace`

## Theme

- Background: `#FFFFFF`
- Accent: `#F97316`
- Primary text: `#111827`
- Borders/surfaces: `#E5E7EB` and `#F9FAFB`

## Environment Variables

Create `client/.env`:

```bash
VITE_API_URL=http://localhost:8000
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-public-anon-key
```

## Run

```bash
cd client
npm install
npm run dev
```

Open: `http://localhost:5173`

## Routing Flow

1. Unauthenticated users land on `/login` or `/signup`.
2. After login/signup, app redirects to `/workspace`.
3. `/workspace`:
   - If workspace exists: redirect to `/app/upload`
   - If workspace is missing: show create workspace card
4. `/app/*` is protected and uses a shared shell:
   - `/app/upload`
   - `/app/chat`
   - `/app/workspace`

## API Contracts Used

- `GET /workspaces/me`
- `POST /workspaces`
- `GET /documents`
- `POST /documents/upload-prepare`
- `POST /documents/upload-complete`
- `GET /documents/{id}`
- Optional: `GET /usage/today` (fallbacks to workspace usage if unavailable)

All API requests include:

```http
Authorization: Bearer <access_token>
```

Behavior:
- Global `401` handling signs out and redirects to `/login`
- `/app/upload` polls documents every 4 seconds while docs are still processing

## Upload Pipeline UX

Per file upload task states:

- `queued`
- `preparing`
- `uploading`
- `completing`
- backend-driven: `extracting`, `indexing`, `indexed`, `failed`

The upload queue supports multiple files (up to 100) with client-side concurrency limit of 4.

## Manual Test Plan

1. Sign up or log in.
2. Confirm redirect to `/workspace`.
3. If prompted, create workspace.
4. Confirm redirect to `/app/upload`.
5. Upload multiple PDFs and watch per-file state changes.
6. Wait until at least one document reaches `Indexed`.
7. Select the indexed document from the left sidebar and verify navigation to `/app/chat`.
8. Send a message in chat and verify stub response appears.
9. Open `/app/workspace`, verify usage metrics, document counts, and refresh behavior.
