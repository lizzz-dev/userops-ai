UserOps AI

UserOps AI is a secure, context-aware administrative assistant that lets authenticated workspace operators manage user records through natural-language conversation.

Instead of forcing operators to use rigid CRUD forms or memorize exact commands, the assistant understands multi-turn requests, remembers conversational context, collects missing information one field at a time, safely resolves ambiguous users, and requires confirmation before destructive actions.

Live links

Frontend: https://userops-web.vercel.app

Backend API: https://userops-ai.vercel.app

Backend health: https://userops-ai.vercel.app/health

GitHub repository: https://github.com/lizzz-dev/userops-ai

Project status

UserOps AI currently supports:

Authentication with separate operator accounts

Natural-language create, read, update, list, count, and delete operations

Multi-turn user creation

Context-aware follow-up messages

Duplicate-name clarification

Safe deletion confirmation and cancellation

Friendly validation for invalid email addresses

Bulk-delete protection

Persistent conversation history

Conversation rename and permanent deletion

Workspace-level data isolation

Docker-based local development

PostgreSQL-backed storage

GitHub Actions CI

Production deployment with Vercel and Neon

Why this project exists

Traditional user-management systems rely on forms, filters, and exact field selection. UserOps AI provides a conversational alternative.

An operator can write:

We have a new user called Sara

The assistant then asks for missing information:

What email address should I use for Sara?

The conversation can continue naturally:

sara@example.com
skip phone
her city should be Islamabad
create now

The assistant maintains the current user, current intent, pending operation, missing fields, and candidate selections across the conversation.

Core features

Authentication

Operator sign-up and sign-in

Password hashing

JWT-based authenticated sessions

HttpOnly cookie authentication

Session restoration after refresh

Logout

Workspace-aware data isolation

Operator accounts are separate from the user records managed by the chatbot.

Natural-language user management

The assistant supports:

Create users

Find users

List users

Count users

Update user details

Delete users safely

Review recent activity

Users can be referenced by:

Full name

First name when unique

Email address

Integer user ID

Follow-up references such as her, him, that user, or the second one

Multi-turn creation

The assistant collects missing fields one at a time.

Add Ayesha

What email address should I use for Ayesha?

ayesha@example.com

Optional fields such as phone and city can be skipped.

Friendly validation

Invalid values are handled before database creation.

ayesha.com

Expected response:

That email address is not valid. Please enter a complete address such as name@example.com.

The unfinished draft is preserved until a corrected value is provided.

Context-aware follow-ups

Examples:

Show Zara Khan
her city should be Islamabad now

Delete Zara
actually don't delete her

Pronouns refer to the current selected user. The system does not infer or store gender from a person's name.

Duplicate-name clarification

The assistant never guesses when multiple records share a name.

1. Zara Khan — zara.khan@example.com
2. Zara Ali — zara.ali@example.com

The operator can reply:

The second one

Safe deletion

Deletion requires explicit confirmation. Old or cancelled confirmation tokens cannot be reused.

Bulk-delete protection

Bulk deletion is intentionally unsupported. The assistant asks the operator to select one user at a time.

Conversation management

Persistent conversation history

Sidebar conversation list

Restore full chat history

Auto-generated titles

Rename conversations

Permanently delete conversations

Refresh persistence

Frontend experience

Custom UserOps AI branding

Responsive dark interface

Empty states

Quick-action suggestions

Thinking animation

Toast notifications

/ shortcut to focus the input

Safe confirmation controls

Example commands

Create

Add a user called Sara
We have a new user named Ahmed
Create Zara Khan with email zara@example.com

Read

Show Zara
Find Zara Khan
Where is Ali?
Find ali.one@example.com
Show user ID 8

List and count

List all users
Show me every user
How many users are there?

Update

Change Zara Khan's city to Islamabad
Her city should be Dubai now
Change his phone number instead

Delete

Delete Zara
Remove the user with email zara@example.com
Actually don't delete her

Architecture

Next.js frontend
        │
        │ same-origin /api proxy
        ▼
FastAPI backend
        │
        ├── Assistant interpreter
        ├── Command parser
        ├── Dialogue manager
        ├── User resolver
        ├── Conversation service
        └── Audit service
        │
        ▼
Neon PostgreSQL

Technology stack

Frontend

Next.js

React

TypeScript

Tailwind CSS

Backend

FastAPI

Python

SQLAlchemy

Pydantic

JWT authentication

Argon2 password hashing

Groq through an OpenAI-compatible client

Infrastructure

Neon PostgreSQL

Vercel for frontend and backend

Docker and Docker Compose for local development

GitHub Actions for CI

Project structure

userops-ai/
├── backend/
│   ├── app/
│   ├── tests/
│   ├── index.py
│   ├── Dockerfile
│   ├── pyproject.toml
│   └── requirements.txt
├── frontend/
│   ├── public/
│   ├── src/
│   ├── Dockerfile
│   └── package.json
├── .github/workflows/ci.yml
├── .env.example
├── .gitignore
├── docker-compose.yml
├── docker-compose.prod.yml
├── DEPLOYMENT.md
└── README.md

Local setup

git clone https://github.com/lizzz-dev/userops-ai.git
cd userops-ai

Create the environment file:

cp .env.example .env

Windows PowerShell:

Copy-Item .env.example .env

Start the application:

docker compose up --build

Local services:

Frontend: http://localhost:3001

Backend: http://localhost:8000

Health check: http://localhost:8000/health

Stop the application:

docker compose down

Development checks

Backend

cd backend
python -m ruff check app tests
python -m pytest -q

Frontend

cd frontend
npm ci
npm run typecheck
npm run lint
npm run build

Production deployment

The current production setup is:

Frontend: Vercel

Backend: Vercel

Database: Neon PostgreSQL

AI provider: Groq

CI: GitHub Actions

See DEPLOYMENT.md for complete instructions.

Security notes

Passwords are hashed.

Authentication uses HttpOnly cookies.

Environment files are excluded from Git.

Workspace data is isolated by operator.

Destructive actions require confirmation.

Raw internal errors are converted into user-friendly responses.

Audit logging is included.

Current scope

UserOps AI does not:

Delete multiple users in one action

Infer personal attributes from names

Execute arbitrary database queries

Bypass deletion confirmation

Replace enterprise identity-governance software

Future improvements

Role-based permissions

User import and export

Advanced audit filtering

Password reset

Email verification

Rate limiting

Browser-level end-to-end tests

Production monitoring

Author

Developed as an AI chatbot internship test project.

GitHub: https://github.com/lizzz-dev