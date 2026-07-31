# Deployment Guide

This guide deploys UserOps AI with:

- **Frontend:** Vercel
- **Backend:** Render
- **Database:** Render PostgreSQL
- **Language understanding:** OpenAI API

## Prerequisites

Prepare:

- GitHub account
- Vercel account
- Render account
- OpenAI API key
- Project pushed to a GitHub repository

Never commit:

- `.env`
- API keys or secrets
- `node_modules`
- `.next`
- local database files

## 1. Push the Project to GitHub

Create a GitHub repository and push the contents of `userops-ai`.

Before pushing, confirm:

```bash
git status
```

Verify that `.env`, `node_modules`, `.next`, Python caches, and local test databases are not staged.

## 2. Deploy the Backend and Database on Render

The repository includes `render.yaml`, which defines the FastAPI service and PostgreSQL database.

1. Sign in to Render.
2. Create a **Blueprint**.
3. Select the GitHub repository.
4. Render reads `render.yaml` and proposes:
   - `userops-api`
   - `userops-db`
5. Provide the environment variables marked as manual.

Set:

```text
OPENAI_API_KEY=<your OpenAI API key>
ALLOWED_ORIGINS=<temporary frontend URL or placeholder>
```

The Blueprint already configures:

```text
DATABASE_URL
SECRET_KEY
ENVIRONMENT=production
COOKIE_SECURE=true
COOKIE_SAMESITE=lax
AI_ENABLED=true
OPENAI_MODEL=gpt-5.6-luna
```

After deployment, copy the backend URL:

```text
https://your-userops-api.onrender.com
```

Verify:

```text
https://your-userops-api.onrender.com/health
```

Expected response:

```json
{"status":"healthy"}
```

## 3. Deploy the Frontend on Vercel

1. Sign in to Vercel.
2. Import the same GitHub repository.
3. Set **Root Directory** to:

```text
frontend
```

4. Add this environment variable:

```text
BACKEND_URL=https://your-userops-api.onrender.com
```

5. Deploy the frontend.
6. Copy the Vercel URL:

```text
https://your-project.vercel.app
```

The Next.js application proxies `/api/*` to FastAPI, so the OpenAI key and backend URL are never exposed in client-side code.

## 4. Finalize Render CORS Configuration

Return to the Render backend environment settings and set:

```text
ALLOWED_ORIGINS=https://your-project.vercel.app
```

Redeploy the backend.

## 5. Verify Production

Test the deployed application in this order:

1. Create an operator account.
2. Log out and sign back in.
3. Refresh and confirm session restoration.
4. Start a multi-turn creation:

```text
We have a new employee called Sara
Use sara@example.com for her
03001234567
She lives in Lahore
```

5. Find Sara and say:

```text
She moved to Islamabad recently
```

6. Create two users named Ali and test:

```text
Delete Ali
The Karachi one
Actually don't delete him
```

7. Test list, count, and recent activity.
8. Create a second operator account and verify workspace isolation.
9. Confirm that browser network requests use `/api/*` and do not reveal `OPENAI_API_KEY`.

## 6. AI Configuration Checks

The backend uses OpenAI only when both conditions are true:

```text
AI_ENABLED=true
OPENAI_API_KEY is configured
```

If the API is unavailable, the assistant uses its deterministic context-aware fallback instead of crashing. The UI displays whether the current response used **AI understanding** or **Safe fallback**.

## 7. Cookie and Domain Notes

The frontend calls the same-origin Next.js `/api` proxy. The backend sets an HttpOnly authentication cookie.

Production values should remain:

```text
COOKIE_SECURE=true
COOKIE_SAMESITE=lax
```

After changing domains or environment variables, redeploy both services and clear old browser cookies before retesting authentication.

## Hosting Notes

Free hosting tiers may sleep after inactivity. The first request can therefore take longer while services wake up. Open the deployed application shortly before a time-sensitive evaluation.
