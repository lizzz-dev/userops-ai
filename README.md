# UserOps AI

UserOps AI is a secure, context-aware administrative assistant that lets authenticated workspace operators manage user records through natural conversation.

Instead of forcing operators to use rigid CRUD forms or memorize exact commands, the assistant understands varied wording, remembers the current user and unfinished operation, collects missing information across messages, clarifies duplicate names, and requires confirmation before destructive actions.

## Project Objective

The objective of UserOps AI is to replace repetitive user-management workflows with a conversational interface while preserving deterministic backend validation, workspace isolation, auditability, and safe database operations.

## Core Features

### Conversational Assistant

- LLM-powered natural-language interpretation through the OpenAI Responses API
- Strict structured AI output validated with Pydantic
- Persistent conversation state and server-side message history
- Multi-turn user creation with missing-field collection
- Pronoun and follow-up support such as `her`, `him`, `that person`, and `use this email for her`
- Duplicate-name clarification with ordinal and descriptive selection
- Context-aware updates such as `She moved to Islamabad`
- Intent switching such as cancelling deletion and updating instead
- Natural confirmation and cancellation
- Deterministic fallback mode when the AI service is unavailable

### User Management

- Create managed users
- Find users by name, email, or integer ID
- Update name, phone, or city
- List and count workspace users
- Review recent user-management activity
- Delete users only after explicit confirmation
- Keep each operator account's managed users isolated

### Authentication and Security

- Operator account registration, login, logout, and session restoration
- Argon2 password hashing
- Signed JWT authentication in an HttpOnly cookie
- Protected chat and user-management endpoints
- Account-scoped conversations, users, and audit logs
- Backend-only OpenAI API key handling

## Technology Stack

### Frontend

- Next.js 16
- React 19
- TypeScript
- Tailwind CSS

### Backend

- FastAPI
- SQLAlchemy
- Pydantic
- OpenAI Python SDK

### Data and Authentication

- PostgreSQL 16
- Argon2 password hashing
- JWT session cookies

### DevOps

- Docker
- Docker Compose
- GitHub Actions
- Render Blueprint configuration

## System Architecture

```text
Browser
   │
   ▼
Next.js Frontend
   │  same-origin /api proxy
   ▼
FastAPI Backend
   ├── Authentication
   ├── Conversation State
   ├── LLM Interpreter
   ├── Dialogue Manager
   ├── Safe CRUD Services
   └── Audit Service
          │
          ▼
     PostgreSQL
```

The language model interprets the operator's meaning and returns a strict structured decision. The dialogue manager applies conversation context and safety rules. Only deterministic backend services are allowed to read or modify PostgreSQL.

## Project Structure

```text
userops-ai/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── db/
│   │   ├── models/
│   │   ├── schemas/
│   │   └── services/
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   ├── public/
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
├── docker-compose.prod.yml
├── render.yaml
├── DEPLOYMENT.md
├── README.md
└── .env.example
```

## Quick Start

### Prerequisites

- Docker Desktop
- Docker Compose
- OpenAI API key for full AI understanding

Clone the repository and enter the project directory:

```bash
git clone <repository-url>
cd userops-ai
```

Create `.env` from the example file and add your backend-only API key:

```bash
cp .env.example .env
```

```env
OPENAI_API_KEY=your_openai_api_key
AI_ENABLED=true
OPENAI_MODEL=gpt-5.6-luna
```

Start the application:

```bash
docker compose up --build
```

Open:

- Frontend: `http://localhost:3001`
- API documentation: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`

Create an operator account from the application and start a conversation.

> Without an OpenAI API key, the application remains usable through its deterministic context-aware fallback interpreter. Full natural-language flexibility requires the configured AI provider.

## Conversation Examples

### Multi-turn creation

```text
Operator: We have a new employee called Sara.
Assistant: What email address should I use for Sara?
Operator: Use sara@example.com for her.
Assistant: What is Sara's phone number? You can say "skip" or "create now".
Operator: 03001234567
Assistant: Which city should I save for Sara?
Operator: She lives in Lahore.
Assistant: Done — Sara was created successfully.
```

### Context-aware update

```text
Operator: Show me Ayesha.
Assistant: I found Ayesha Khan.
Operator: She moved to Islamabad recently.
Assistant: Done — I updated city for Ayesha Khan.
```

### Duplicate clarification and cancellation

```text
Operator: Delete Ali.
Assistant: I found multiple matching users. Which one do you mean?
Operator: The Karachi one.
Assistant: Ali will be permanently deleted. Should I continue?
Operator: Actually don't delete him.
Assistant: Deletion cancelled. Ali was not changed.
```

### Intent switching

```text
Operator: Delete Sara.
Assistant: Should I continue?
Operator: No, change her number instead.
Assistant: What should Sara's new phone be?
```

### Other supported requests

```text
List all users
How many users are there?
Show recent activity
Show user with ID 3
Who were we editing?
What information is still missing?
Show that person again
```

## Conversation State

The backend stores conversations and messages in PostgreSQL. Each conversation tracks:

- current workflow status
- active operation
- field currently being requested
- selected user
- unfinished user draft
- duplicate candidates
- pending destructive action

Conversation ownership is checked against the authenticated operator account.

## Environment Variables

Copy `.env.example` to `.env` for local overrides.

Important variables:

```env
POSTGRES_DB=userops
POSTGRES_USER=userops
POSTGRES_PASSWORD=replace_with_a_strong_local_password
SECRET_KEY=replace_with_a_long_random_secret
AI_ENABLED=true
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-5.6-luna
```

Production also requires:

```env
DATABASE_URL=postgresql://user:password@host:5432/database
ENVIRONMENT=production
COOKIE_SECURE=true
ALLOWED_ORIGINS=https://your-frontend-domain
```

Never commit `.env` or expose `OPENAI_API_KEY` in frontend code.

## Development Checks

Backend:

```bash
cd backend
pip install -r requirements-dev.txt
pytest -q
ruff check app tests
```

Frontend:

```bash
cd frontend
npm ci
npm run typecheck
npm run lint
npm run build
```

## Automated Test Coverage

The backend test suite covers:

- signup, login, logout, and invalid credentials
- complete CRUD workflow
- assignment-compatible email-only creation
- multi-turn creation
- pronoun-based updates
- duplicate-name clarification
- ordinal and descriptive candidate selection
- natural deletion cancellation
- switching from deletion to update
- conversation history and ownership
- account workspace isolation
- activity logging

## Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for the Vercel, Render, PostgreSQL, and OpenAI environment configuration.

## Future Improvements

- Email verification and password reset
- Role-based permissions and organization invitations
- Conversation list and search interface
- Analytics dashboard
- Rate limiting and abuse protection
- Database migration tooling such as Alembic
- Additional AI-provider adapters
- Voice interaction
