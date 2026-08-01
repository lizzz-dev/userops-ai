UserOps AI

UserOps AI is a secure, context-aware administrative assistant that lets authenticated workspace operators manage user records through natural-language conversation.

Instead of forcing operators to use rigid CRUD forms or memorize exact commands, the assistant understands multi-turn requests, remembers conversational context, collects missing information one field at a time, safely resolves ambiguous users, and requires confirmation before destructive actions.

Repository: https://github.com/lizzz-dev/userops-ai

Project status

UserOps AI currently supports:

Authentication with separate operator accounts

Natural-language create, read, update, list, count, and delete operations

Multi-turn user creation

Context-aware follow-up messages

Duplicate-name clarification

Safe deletion confirmation and cancellation

Persistent conversation history

Conversation rename and permanent deletion

Docker-based local development

PostgreSQL-backed storage

Production deployment setup for Render and Vercel

Deployment links can be added here after production deployment:

Frontend: Frontend: https://userops-web.vercel.app

Backend API: https://userops-ai.vercel.app

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

Users can be referenced by:

Full name

First name when unique

Email address

Integer user ID

Follow-up references such as her, him, that user, or the second one

Multi-turn creation

The assistant collects missing fields one at a time.

Example:

Add Ayesha

What email address should I use for Ayesha?

ayesha@example.com

What is Ayesha's phone number? You can say "skip" or "create now".

Optional fields such as phone and city can be skipped.

Friendly validation

Invalid values are handled before database creation.

Example:

ayesha.com

Expected response:

That email address is not valid. Please enter a complete address such as name@example.com.

The assistant keeps the unfinished draft and waits for a corrected value instead of exposing raw backend validation errors.

Context-aware follow-ups

The dialogue manager remembers the active user and pending operation.

Examples:

Show Zara Khan
her city should be Islamabad now

Find Ali
change his number instead

Delete Zara
actually don't delete her

Pronouns refer to the current selected user. The system does not infer or store gender from a person's name.

Duplicate-name clarification

The assistant never guesses when multiple records share a name.

Example:

Show Zara

If two matching users exist, the assistant presents numbered choices and waits for a selection:

1. Zara Khan — zara.khan@example.com
2. Zara Ali — zara.ali@example.com

The operator can reply:

The second one

Safe deletion

Deletion requires explicit confirmation.

Example:

Delete Zara Khan

The assistant shows the selected record and asks for confirmation before deleting it.

The operator can:

Confirm deletion

Cancel deletion

Say actually don't delete her

Start another operation, which safely clears the old pending deletion

Old or cancelled confirmation tokens cannot be reused.

Bulk-delete protection

Bulk deletion is intentionally unsupported.

Example:

Delete both of them

The assistant explains that destructive actions must be completed one user at a time and asks the operator to choose a single user.

This prevents accidental multi-record deletion.

Conversation management

Conversation history stored in the database

Conversation list in the sidebar

Restore full chat history

Auto-generated conversation titles

Rename conversations

Permanently delete conversations

Refresh persistence

Current-conversation switching

Polished frontend experience

Custom UserOps AI branding

Responsive dark interface

Empty conversation state

Quick action suggestions

Thinking animation

Success and error toast notifications

/ keyboard shortcut to focus the chat input

Confirmation controls for destructive actions

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
Update user ID 8
Change his phone number instead

Delete

Delete Zara
Remove the user with email zara@example.com
Actually don't delete her

Safety and dialogue rules

UserOps AI follows several deterministic safety rules:

Never guess between duplicate names.

Require confirmation before deletion.

Allow only one destructive deletion at a time.

Clear stale candidate selections when a fresh request starts.

Reject invalid email addresses before database creation.

Do not expose raw Pydantic or database errors to the user.

Keep unfinished create drafts isolated from existing users.

Prevent stale confirmation tokens from executing cancelled actions.

Use deterministic CRUD services after natural-language interpretation.

Treat pronouns as references to the current selected user, not as gender inference.

Architecture

┌──────────────────────────────┐
│ Next.js Frontend             │
│ Chat UI, Auth UI, History    │
└──────────────┬───────────────┘
               │ HTTP / JSON
               ▼
┌──────────────────────────────┐
│ FastAPI Backend              │
│ Auth, Chat API, CRUD API     │
├──────────────────────────────┤
│ Assistant Interpreter        │
│ Command Parser               │
│ Dialogue Manager             │
│ User Resolver                │
│ Conversation Service         │
│ Audit Service                │
└──────────────┬───────────────┘
               │ SQLAlchemy
               ▼
┌──────────────────────────────┐
│ PostgreSQL                   │
│ Operators, Users, Chats      │
│ Messages, Audit Logs         │
└──────────────────────────────┘

Request flow

The frontend sends a natural-language message to the FastAPI chat endpoint.

The interpreter identifies the intent and extracts structured fields.

The dialogue manager applies conversation state and safety rules.

The resolver identifies the correct user by name, email, or ID.

Deterministic services perform the database operation.

The assistant returns a structured reply, updated context, and optional UI actions.

The conversation and messages are persisted for later restoration.

Technology stack

Frontend

Next.js

React

TypeScript

Custom component-based interface

API proxying to the backend

Backend

FastAPI

Python

SQLAlchemy

Pydantic

JWT authentication

Argon2 password hashing

Groq through an OpenAI-compatible client

Deterministic dialogue and CRUD services

Database and infrastructure

PostgreSQL

Docker

Docker Compose

Render deployment configuration

Vercel-ready frontend

Project structure

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
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── app/
│   │   ├── components/
│   │   └── lib/
│   ├── Dockerfile
│   └── package.json
├── .env.example
├── .gitignore
├── docker-compose.yml
├── docker-compose.prod.yml
├── render.yaml
├── DEPLOYMENT.md
└── README.md

Local setup

Requirements

Install:

Git

Docker Desktop

Docker Compose

Node.js

Python

1. Clone the repository

git clone https://github.com/lizzz-dev/userops-ai.git
cd userops-ai

2. Create the environment file

Copy the example file:

cp .env.example .env

On Windows PowerShell:

Copy-Item .env.example .env

Fill in the required values in .env.

Use .env.example as the source of truth for the exact variable names required by the current codebase.

Typical configuration includes:

PostgreSQL connection values

JWT/authentication secret

Groq API key

AI base URL and model settings

Allowed frontend origins

Backend URL used by the frontend

Never commit the real .env file.

3. Start the application

docker compose up --build

Local services:

Frontend: http://localhost:3001

Backend: http://localhost:8000

Health check: http://localhost:8000/health

4. Stop the application

docker compose down

To remove local database volumes as well:

docker compose down -v

Use the volume-removal command carefully because it deletes local database data.

Development commands

Backend tests

cd backend
python -m pytest -q

Backend syntax checks

python -m py_compile app/services/assistant_interpreter.py
python -m py_compile app/services/command_parser.py
python -m py_compile app/services/dialogue_manager.py

Frontend checks

cd frontend
npm install
npm run typecheck
npm run lint
npm run build

Important API areas

The application includes routes for:

Authentication

User CRUD

Natural-language chat

Chat confirmation

Conversation listing

Conversation restoration

Conversation rename

Permanent conversation deletion

Health checks

The chat API returns structured responses containing the assistant reply, status, conversation context, optional record data, and safe UI actions.

Testing scenarios

A strong end-to-end test should include:

Create flow

Add Ayesha
ayesha.com
sorry, use ayesha@gmail.com
skip phone
skip city

Verify that:

The invalid email is rejected politely.

The draft remains active.

The corrected email is accepted.

The user is created successfully.

Context-aware update

Show Ayesha
her city should be Islamabad now

Verify that the saved city is exactly:

Islamabad

Delete cancellation

Delete Ayesha
Actually don't delete her
Find Ayesha

Verify that Ayesha still exists.

Duplicate clarification

Create two users with the same first name and run:

Show Zara

Verify that the assistant asks the operator to select one instead of guessing.

Bulk-delete guard

List all users
Delete both of them

Verify that no user is automatically deleted.

Conversation features

Verify:

History survives refresh

An old conversation can be restored

Rename persists

Permanent delete removes the conversation

Logout and login preserve workspace data

Deployment

The intended production setup is:

Frontend: Vercel

Backend: Render

Database: Render PostgreSQL

The repository contains:

render.yaml

docker-compose.prod.yml

DEPLOYMENT.md

Follow the detailed steps in DEPLOYMENT.md.

After deployment, update the links near the top of this README.

Design decisions

Why use AI plus deterministic services?

The language model is used to interpret natural language, but it does not directly mutate the database.

Database changes are performed by deterministic services after validation, resolution, permission checks, and safety rules.

This provides a better balance between conversational flexibility and predictable CRUD behavior.

Why not support bulk deletion?

Bulk deletion is intentionally blocked because it is a high-risk destructive operation. Requiring one user and one confirmation at a time prevents accidental data loss.

Why not infer gender from pronouns?

The user model does not contain a gender field. Pronouns such as her, him, and their refer to the current selected user in conversation state. The system does not guess gender from names.

Why preserve conversation state?

Without state, follow-up requests such as her email is..., the second one, or actually don't delete him cannot be interpreted reliably. The dialogue manager stores the active intent, selected user, pending action, missing field, and candidate list.

Security notes

Passwords are hashed and never stored as plain text.

Authentication uses secure session handling.

Real environment files are excluded from Git.

Workspace data is isolated by the authenticated operator.

Destructive operations require confirmation.

Old confirmation tokens are invalidated after cancellation or context changes.

Raw internal validation errors are converted into user-friendly responses.

Audit logging is included for administrative operations.

Current scope

UserOps AI is designed as a focused user-management assistant.

It does not attempt to:

Delete multiple users in one action

Infer personal attributes from names

Execute arbitrary database queries

Bypass deletion confirmation

Replace full enterprise identity-governance software

The project demonstrates a safe, conversational CRUD architecture with persistent context and production-oriented UI/UX.

Future improvements

Possible future additions include:

Role-based operator permissions

User import and export

Advanced audit-log filtering

Workspace analytics

Password-reset flow

Email verification

Rate limiting

Automated end-to-end browser tests

Production monitoring and alerting

Author

Developed as an AI CHATBOT test project.

GitHub: https://github.com/lizzz-dev