# TicketFlow

TicketFlow is a FastAPI support-ticket API with role-aware queues, collaborative ticket conversations, and operational triage tools.

## Highlights

- Secure registration and bearer-token authentication
- Customer-owned queues with administrator-wide visibility
- Ticket priority (`LOW` through `URGENT`), category, lifecycle status, and agent response
- Search, filtering, sorting, and pagination for busy ticket queues
- Comment threads so customers and support staff can collaborate in context
- Immutable activity timelines for ticket creation, triage, and comment events
- Permission-aware dashboard counts for open work and urgent/high-priority issues
- Prometheus-compatible metrics at `/metrics`

## Run locally

Set `DATABASE_URL` to a PostgreSQL async URL, for example:

```bash
export DATABASE_URL='postgresql+asyncpg://postgres:postgres@localhost:5432/ticketing_db'
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The application applies Alembic migrations at startup. Explore the interactive API workspace at [http://localhost:8000/docs](http://localhost:8000/docs).

## Run with Docker

Docker Compose starts PostgreSQL and the API together:

```bash
docker compose up --build
```

The API is available at `http://localhost:8000`; PostgreSQL is exposed locally on port `5433`. For a fresh database, stop the stack and remove its named volume with `docker compose down -v`.

## Configuration

| Variable | Required | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | Yes | Async PostgreSQL connection string, e.g. `postgresql+asyncpg://user:password@host:5432/database` |
| `SECRET_KEY` | Yes in production | Signing key for JWT access tokens. Use a long random value outside local development. |
| `REDIS_URL` | Optional | Celery broker/result backend. Notifications fall back to application logs when it is unavailable. |

Never use the repository's development `SECRET_KEY` value in a deployed environment.

## Quick start: authenticate and create a ticket

Register a customer account:

```bash
curl -X POST http://localhost:8000/register \
  -H 'Content-Type: application/json' \
  -d '{"name":"Ada Lovelace","username":"ada","password":"use-a-strong-password"}'
```

Get an access token. The login route follows the OAuth2 form convention:

```bash
curl -X POST http://localhost:8000/login \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=ada&password=use-a-strong-password'
```

Use the returned `access_token` as `TOKEN`, then create a ticket:

```bash
curl -X POST http://localhost:8000/tickets \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "title":"Cannot open billing portal",
    "description":"The page returns an error after I sign in.",
    "priority":"HIGH",
    "category":"BILLING"
  }'
```

## Ticket workspace endpoints

| Endpoint | What it does |
| --- | --- |
| `GET /tickets` | Queue with `status`, `priority`, `category`, `q`, `page`, `page_size`, and `sort` controls |
| `GET /tickets/dashboard` | Open-work and priority snapshot scoped to the signed-in user |
| `PATCH /tickets/{id}` | Admin triage updates: status, priority, category, and response |
| `GET/POST /tickets/{id}/comments` | View and add conversation messages |
| `GET /tickets/{id}/activity` | View the chronological audit trail |

Use `POST /login` with form fields (`username`, `password`) to obtain a bearer token, then authorize it in the API docs.

## Ticket lifecycle and triage

Tickets begin in `OPEN`. Administrators can update a ticket with `PATCH /tickets/{id}` and use the following lifecycle states:

| Status | Use when |
| --- | --- |
| `OPEN` | The ticket has been received but is not yet being worked. |
| `IN_PROGRESS` | An agent is actively investigating or fixing it. |
| `WAITING_ON_CUSTOMER` | More information or action is needed from the requester. |
| `RESOLVED` | A fix or answer has been provided. |
| `CLOSED` | The work is complete and the ticket is no longer active. |

Priorities are `LOW`, `MEDIUM`, `HIGH`, and `URGENT`. `sort=priority` places urgent work first. Categories are free-form short labels and are normalized to uppercase when a ticket is created or updated.

Example admin triage update:

```bash
curl -X PATCH http://localhost:8000/tickets/42 \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"status":"IN_PROGRESS","priority":"URGENT","response":"We are investigating this now."}'
```

## Queue queries and dashboard

`GET /tickets` supports these optional query parameters:

| Parameter | Example | Description |
| --- | --- | --- |
| `status` | `OPEN` | Filter by lifecycle status. |
| `priority` | `HIGH` | Filter by urgency. |
| `category` | `BILLING` | Filter by category. |
| `q` | `portal` | Case-insensitive search across title and description. |
| `page` / `page_size` | `2` / `25` | Paginate results; page size is limited to 100. |
| `sort` | `priority` | `newest` (default), `oldest`, or `priority`. |

For example: `GET /tickets?status=OPEN&priority=HIGH&sort=priority`. Queue results include `items`, `total`, `page`, and `page_size`. `GET /tickets/dashboard` provides current open-work totals and the counts of high- and urgent-priority tickets. Customers only see their own work; administrators see the full queue.

## Roles and permissions

| Capability | Customer | Admin |
| --- | --- | --- |
| Create and view own tickets | Yes | Yes |
| Search the full queue | No | Yes |
| Add/view comments on accessible tickets | Yes | Yes |
| Change ticket status, priority, category, or response | No | Yes |
| Manage users and delete tickets | No | Yes |

Accounts created through `/register` are customers by default. Create or promote administrator accounts through your trusted provisioning workflow before exposing the API publicly.

## Architecture

```text
FastAPI routes → authentication dependencies → SQLAlchemy async session → PostgreSQL
       │                    │
       └── Prometheus       └── background notification → Celery/Redis (optional)
```

- `app/routers/` contains HTTP endpoints.
- `app/models/` contains SQLAlchemy database models.
- `app/schemas/` defines validated request and response payloads.
- `alembic/versions/` tracks database migrations.
- `app/metrics.py` exposes Prometheus metrics at `/metrics`.
- `app/services/` contains reusable application workflows, including audit logging.

## Development

Run the test suite after installing dependencies:

```bash
pytest -q
```

Create a new migration after model changes:

```bash
alembic revision --autogenerate -m "describe the change"
alembic upgrade head
```

Review autogenerated migrations before applying them, especially around destructive schema changes.
