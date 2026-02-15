# Client (`client/`)

Frontend for Enterprise RAG v1 scope using React + Vite + TypeScript + Tailwind.

Implemented scope:
- Supabase Auth (`/login`, `/signup`)
- Protected Home (`/home`)
- Workspace create/show (one workspace per user)
- Daily usage UI (used/reserved/remaining/limit/resets_at)
- Diagnostics accordion for `GET /auth/me` and `GET /workspaces/me`

Design system:
- Orange + Black + White palette only
- Theme tokens in `src/styles/theme.ts`
- Tailwind custom tokens in `tailwind.config.ts`

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

## Routes

- `/login` sign-in page
- `/signup` sign-up page
- `/home` protected home page

## API Integration

All backend requests include:

```http
Authorization: Bearer <access_token>
```

Endpoints used:
- `GET /auth/me`
- `POST /workspaces`
- `GET /workspaces/me`

Behavior:
- `401` => auto sign-out + redirect to `/login`
- `409` on workspace create => fetch existing `/workspaces/me` and display
