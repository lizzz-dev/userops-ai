# UserOps AI frontend

Next.js App Router frontend for UserOps AI. Run the complete stack from the repository root with `docker compose up --build`.

The browser calls relative `/api/*` routes. `next.config.ts` proxies them to the FastAPI service configured by `BACKEND_URL`.
