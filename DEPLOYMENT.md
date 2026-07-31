Deployment Guide

This guide deploys the current UserOps AI architecture with:

Frontend: Vercel (Next.js)

Backend: Vercel (FastAPI on the Python runtime)

Database: Neon PostgreSQL

Language understanding: Groq through an OpenAI-compatible client

Source control and CI: GitHub and GitHub Actions

The older Render/OpenAI deployment instructions are no longer used by this project.

Production URLs

Backend API: https://userops-ai.vercel.app

Backend health check: https://userops-ai.vercel.app/health

Frontend: add the final Vercel frontend URL after deployment

Prerequisites

Prepare:

GitHub account

Vercel account

Neon account

Groq API key

Project pushed to GitHub

Green GitHub Actions checks for both backend and frontend

Never commit:

.env

API keys or secrets

Neon connection strings

node_modules

.next

Python caches

Local test databases

The repository .gitignore should exclude all private and generated files while allowing .env.example.

1. Push and verify the repository

The repository is:

https://github.com/lizzz-dev/userops-ai

Before pushing changes:

git status

Run the local checks:

cd backend
python -m ruff check app tests
python -m pytest -q
cd ..

cd frontend
npm run typecheck
npm run lint
npm run build
cd ..

Commit and push:

git add .
git commit -m "Describe the change"
git push

On GitHub, verify:

CI / backend   passed
CI / frontend  passed

2. Create the Neon PostgreSQL database

Sign in to Neon.

Create a project named:

userops-ai

Open the project and click Connect.

Copy the PostgreSQL connection string.

Keep the string private.

It should look similar to:

postgresql://USER:PASSWORD@HOST/DATABASE?sslmode=require

For a serverless application, a pooled Neon connection string is appropriate. The host normally contains -pooler.

This complete string is used as the backend DATABASE_URL.

Do not split it into POSTGRES_USER, POSTGRES_PASSWORD, and POSTGRES_DB unless the code is explicitly changed to use those variables.

3. Backend files required by Vercel

The backend project root is:

backend

The repository includes:

backend/index.py

with:

from app.main import app

The exported FastAPI app is the Vercel Python entry point.

The backend pyproject.toml includes:

Python project metadata

Runtime dependencies

Python version requirement

Pytest configuration

Ruff configuration

Keep requirements.txt as well because it is still useful for Docker and local development.

4. Deploy the FastAPI backend on Vercel

Create the backend project

Open Vercel.

Select Add New → Project.

Import:

lizzz-dev/userops-ai

Configure:

Project name: userops-ai
Root Directory: backend
Framework Preset: Other / FastAPI
Branch: main

Do not set a frontend output directory for this project.

Production environment variables

Open:

Project Settings → Environments → Production

Create the following variables inside the Production environment:

DATABASE_URL
SECRET_KEY
ENVIRONMENT
COOKIE_SECURE
COOKIE_SAMESITE
AI_ENABLED
OPENAI_API_KEY
OPENAI_BASE_URL
OPENAI_MODEL

Use these values:

DATABASE_URL=<complete Neon connection string>
SECRET_KEY=<long random secret>
ENVIRONMENT=production
COOKIE_SECURE=true
COOKIE_SAMESITE=lax
AI_ENABLED=true
OPENAI_API_KEY=<Groq API key>
OPENAI_BASE_URL=https://api.groq.com/openai/v1
OPENAI_MODEL=openai/gpt-oss-20b

Generate a secure secret locally:

python -c "import secrets; print(secrets.token_urlsafe(64))"

Although the variables use OPENAI_* names for compatibility with the existing client code, the provider is Groq because OPENAI_BASE_URL points to Groq.

Production versus Preview

Vercel stores environment variables separately for:

Production

Preview

Development

The live main branch deployment uses Production variables.

Preview variables are optional and only needed when testing deployments from non-production branches or pull requests.

Deploy or redeploy

After adding or changing environment variables:

Deployments → latest deployment → ⋯ → Redeploy

Environment-variable changes require a new deployment before the running function can use them.

Verify the backend

Open:

https://userops-ai.vercel.app/health

Expected response:

{"status":"healthy"}

A successful health response confirms that the FastAPI function can start with the required production configuration.

Complete database behavior is then verified through sign-up and CRUD operations after the frontend is deployed.

5. Deploy the Next.js frontend on Vercel

Create a second Vercel project from the same repository.

Configure:

Project name: userops-web
Root Directory: frontend
Framework Preset: Next.js
Branch: main

Frontend Production environment variable

Under:

Project Settings → Environments → Production

add:

BACKEND_URL=https://userops-ai.vercel.app

Do not add a trailing slash.

The frontend sends browser requests to its own /api/* routes. The Next.js configuration proxies those requests to the FastAPI backend, so the backend URL and Groq key are not exposed as client-side JavaScript variables.

Deploy the project and copy the frontend URL, for example:

https://userops-web.vercel.app

6. Configure the deployed frontend origin

After obtaining the frontend URL, return to the backend Vercel project.

Under the backend Production environment, add or update:

ALLOWED_ORIGINS=https://YOUR-FRONTEND-DOMAIN.vercel.app

Example:

ALLOWED_ORIGINS=https://userops-web.vercel.app

Then redeploy the backend.

If the backend supports comma-separated origins, multiple trusted domains can be configured when needed.

7. Verify production

Test the live frontend in this order.

Authentication

Create an operator account.

Log in.

Refresh the page and verify session restoration.

Log out and sign in again.

Multi-turn creation

Add Ayesha
ayesha.com
sorry, use ayesha@gmail.com
skip phone
skip city

Verify:

Invalid email receives a friendly response.

No raw Pydantic error is shown.

The draft remains active.

The corrected email is accepted.

Ayesha is created.

Read and context

Show Ayesha
Where is Ayesha?
Find ayesha@gmail.com

Then:

her city should be Islamabad now

Verify that the stored city is exactly:

Islamabad

Delete cancellation

Delete Ayesha
Actually don't delete her
Find Ayesha

Verify that Ayesha still exists.

Delete confirmation

Delete Ayesha

Click Confirm deletion, then verify that Ayesha is no longer found.

Duplicate-name clarification

Create two users with the same first name:

Add Zara Khan with email zara.khan@example.com
Add Zara Ali with email zara.ali@example.com
Show Zara

Verify that the assistant asks for clarification and does not guess.

Reply:

The second one

Verify that the second record is selected.

Bulk-delete guard

List all users
Delete both of them

Verify:

Bulk deletion is refused.

The assistant asks for one user at a time.

No record is automatically deleted.

Conversation management

Verify:

New conversation

Conversation history after refresh

Restore an old conversation

Rename a conversation

Permanently delete a conversation

Thinking animation

Toast messages

/ shortcut to focus the input

Workspace isolation

Create a second operator account.

Confirm that the second operator cannot see the first operator's managed users or conversations.

8. AI configuration checks

The backend uses Groq when:

AI_ENABLED=true
OPENAI_API_KEY is set
OPENAI_BASE_URL=https://api.groq.com/openai/v1
OPENAI_MODEL=openai/gpt-oss-20b

The application uses an OpenAI-compatible client, but requests are sent to Groq through the configured base URL.

If AI interpretation is unavailable, the deterministic parser and dialogue-manager fallback should continue handling supported CRUD workflows safely.

9. Cookie and proxy notes

Production values should remain:

COOKIE_SECURE=true
COOKIE_SAMESITE=lax

Authentication uses an HttpOnly cookie.

The browser calls the frontend's same-origin /api path, and the Next.js proxy forwards requests to FastAPI.

After changing domains, cookies, or environment variables:

Redeploy the affected project.

Clear old site cookies.

Test sign-up, login, refresh, and logout again.

10. Runtime logs and troubleshooting

Backend function crashes

Open:

Vercel backend project → Logs

A crash caused by missing settings typically shows Pydantic validation errors for environment variables such as:

database_url: Field required
secret_key: Field required

Fix the variables under the Production environment and redeploy.

Build fails because pyproject.toml has no project metadata

Ensure backend/pyproject.toml contains a valid:

[project]

section with runtime dependencies.

GitHub backend CI cannot import app

The backend GitHub Actions job must use:

defaults:
  run:
    working-directory: backend

env:
  PYTHONPATH: ${{ github.workspace }}/backend

Frontend cannot reach the backend

Check:

BACKEND_URL=https://userops-ai.vercel.app

Then redeploy the frontend.

Authentication fails only in production

Check:

COOKIE_SECURE=true
COOKIE_SAMESITE=lax
ALLOWED_ORIGINS=<exact frontend URL>

Clear old browser cookies and retry.

11. Update repository documentation

After the frontend deploys, update both README.md and this file with:

Frontend: https://YOUR-FRONTEND-DOMAIN.vercel.app
Backend API: https://userops-ai.vercel.app

Commit the final links:

git add README.md DEPLOYMENT.md
git commit -m "Add final production deployment links"
git push

Final production checklist

Backend /health returns {"status":"healthy"}

Frontend opens from its Vercel URL

Sign-up works

Login and logout work

Session survives refresh

Create, find, list, count, update, and delete work

Invalid emails are handled politely

Duplicate names require clarification

Deletion requires confirmation

Cancellation protects the user

Bulk delete is blocked

Conversation history persists

Conversation rename and delete work

Second operator has isolated workspace data

GitHub backend CI is green

GitHub frontend CI is green

No secrets are committed