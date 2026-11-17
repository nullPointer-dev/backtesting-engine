# Backtester frontend

React + TypeScript + Vite single-page app for the backtesting API.

```bash
cp .env.example .env.local   # point VITE_API_URL at the backend if it isn't on :8000
npm install
npm run dev                  # http://localhost:5173
```

| Script | What it does |
|---|---|
| `npm run dev` | Dev server with hot reload |
| `npm run build` | Type-check and build to `dist/` |
| `npm run typecheck` | Type-check only |
| `npm run lint` | Lint with oxlint |
| `npm run gen:api` | Regenerate `src/api/schema.d.ts` from the backend's OpenAPI schema (run after changing the API) |

API calls go through `src/api/client.ts`, a typed `openapi-fetch` client generated from the backend, so a renamed or removed field fails type-checking here.
