# multi_tenant_saas_subscription_platform

Production-ready FastAPI starter for a multi-tenant SaaS backend with subdomain tenant resolution, SQLAlchemy 2.x, Alembic, and deployment scaffolding for Nginx and systemd.

The root path now serves a lightweight landing page with separate entry points for tenant user login and platform admin login. Tenant users can start from a single email field on the landing page; the backend discovers tenant memberships, sends a magic link immediately for a single tenant, or asks the user to choose a tenant when several memberships exist. Platform admins use the root-host admin login and admin dashboard.

## Architecture

The codebase is organized around three layers:

- `app/` contains the HTTP application, domain modules, middleware, settings, and database integration.
- `worker/` is reserved for asynchronous and background processing entrypoints.
- `deployment/` contains infrastructure-facing templates for Nginx and systemd.

Inside `app/`, domains are grouped by business capability:

- `admin/`
- `tenants/`
- `auth/`
- `organizations/`
- `memberships/`
- `users/`
- `subscriptions/`
- `notifications/`
- `usage/`

Tenant isolation starts at request entry. Middleware resolves the tenant from the `Host` header and loads the tenant into request state. API scope is separated into public, tenant, and admin routers. Tenant-scoped routers reject requests when no tenant context is available.

## Data Model

- One tenant has one organization
- One tenant has many memberships
- One user can belong to many tenants through memberships
- Membership roles are `owner`, `admin`, and `member`

Core relationships:

- `Tenant` has one `Organization`
- `Tenant` has many `Membership`
- `User` has many `Membership`
- `Tenant` and `User` are connected through `Membership`
- `Tenant` has one current `Subscription`
- `Subscription` belongs to one `Plan`

## Setup

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy the environment file and adjust values:

```bash
cp .env.example .env
```

4. Run migrations:

```bash
alembic upgrade head
```

5. Start the API:

```bash
uvicorn app.main:app --host 0.0.0.0 --port "${APP_PORT:-8000}"
```

## Environment

Configuration is loaded from environment variables through `pydantic-settings`. The project expects `.env` to be sourced by the shell or loaded automatically by the settings layer.

## Mail

SMTP is configured through the existing mail environment variables and is now backed by a real SMTP service layer.

- `MAIL_MAILER` must be `smtp`
- `MAIL_HOST`, `MAIL_PORT`, `MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_ENCRYPTION`, `MAIL_FROM_ADDRESS`, and `MAIL_FROM_NAME` define the outbound mail transport
- Supported encryption values are `none`, `tls`, and `ssl`

Verify SMTP connectivity with the current environment:

```bash
python -m app.domains.mail.verify
```

Send a test message:

```bash
python -m app.domains.mail.verify --send-test --to you@example.com
```

## Security

- Keep `.env` and any environment-specific variants out of version control
- Treat `.env.example` as placeholders only and never store real credentials in tracked files
- Rotate application, Stripe, mail, Redis, database, and admin secrets when environments are shared or exposed
- Use non-local `APP_ENV` values only with fully configured runtime secrets

Local secret scan before push:

```bash
gitleaks detect --config .gitleaks.toml --source .
```

## Security Configuration

Recommended production configuration:

- Set `APP_ENV` to a non-local value such as `production`
- Provide `DATABASE_URL`, `SECRET_KEY`, `STRIPE_SECRET_KEY`, and `STRIPE_WEBHOOK_SECRET`
- Keep `APP_DEBUG=false`
- Leave `ENABLE_DOCS` unset or set it to `false` unless docs exposure is intentionally required
- Leave `DEV_AUTH_ENABLED=false`
- Leave `DEV_ADMIN_AUTH_ENABLED=false`
- Set `ALLOWED_HOSTS` to the exact application hosts that should be served
- Set `CORS_ALLOWED_ORIGINS` to explicit trusted origins only

Runtime safety defaults:

- OpenAPI and Swagger are enabled by default only in local environments
- Development header auth is disabled by default, including in local environments, unless `DEV_AUTH_ENABLED=true` or `DEV_ADMIN_AUTH_ENABLED=true`
- Wildcard CORS origins are rejected outside local environments
- Trusted hosts default to the configured application domain in non-local environments
- Invalid Stripe webhook signatures return safe generic errors

## Tenant Resolution

- `APP_DOMAIN` defines the shared root domain, for example `core.glitter.kr`
- Requests to `tenant-a.core.glitter.kr` resolve `tenant-a` as the tenant subdomain
- Requests to the bare application domain do not create tenant context
- Tenant-scoped routes fail with `404` if the tenant is not resolved or is inactive

## Authentication

Password-based authentication and JWT token issuance live in the `auth` domain.

- `POST /api/v1/auth/register` creates a user with a normalized email and hashed password
- `POST /api/v1/auth/login` validates credentials, updates `last_login_at`, and returns JWT access and refresh tokens
- `POST /api/v1/auth/magic-link/start` sends a tenant-scoped sign-in link to the submitted email
- `POST /api/v1/auth/magic-link/consume` verifies the sign-in link, auto-creates the user if needed, and issues tokens
- `POST /api/v1/auth/refresh` accepts a refresh token and returns a rotated refresh token and a new access token
- `POST /api/v1/auth/logout` revokes the presented refresh token session
- Send bearer tokens with `Authorization: Bearer <access_token>`

Access Tokens:

- Short-lived JWTs signed with `SECRET_KEY`
- Include `sub`, `email`, `token_type`, and `exp`
- Intended for authenticated API access

Refresh Tokens:

- Longer-lived JWTs signed with the same application secret
- Must be sent to `/api/v1/auth/refresh`
- Stored server-side only as token hashes in `auth_sessions`
- Rotated on every refresh and revoked on logout

Production deployments should treat Bearer tokens as the supported user authentication path.

Magic Link Entry:

- Tenant user entry is email-first on the tenant login page
- If the email is new, the first verified magic link creates the user automatically
- The same verified flow also creates a tenant membership as `member` when one does not already exist and the tenant seat limit allows it
- Platform admin entry also supports magic links, but only for existing active admin accounts

## Bearer Authentication

Tenant-scoped authenticated requests now use JWT bearer tokens as the primary current-user mechanism.

- Send `Authorization: Bearer <access_token>` with tenant-scoped requests
- Send the tenant `Host` header so middleware can resolve the current tenant context
- Current membership is resolved from the authenticated user and the tenant loaded from `Host`
- Non-members receive `403 Tenant membership required`

Example:

```bash
curl -i http://127.0.0.1:8000/api/v1/me \
  -H "Host: team1.app.local" \
  -H "Authorization: Bearer <access_token>"
```

## Development Authentication

Development authentication exists only to make local verification possible before a real identity layer is integrated.

- Tenant member development auth uses `X-User-Email`
- Admin development auth uses `X-Admin-Key`
- Tenant development auth is used only as a local compatibility fallback when `DEV_AUTH_ENABLED=true`
- Admin development auth is used only as a local compatibility fallback when `DEV_ADMIN_AUTH_ENABLED=true`
- Both mechanisms are accepted only in local-style environments such as `local`, `development`, `dev`, or `test`
- Production-like environments reject these headers with safe `401` responses

This is not production authentication and must not be used as a deployment auth strategy.

In a real deployment, replace these development headers with a proper authentication system such as:

- session or token-based user authentication
- tenant-aware identity claims
- separate privileged admin authentication with audited access controls

## Billing

Billing lives in the `subscriptions` domain and uses Stripe as the system of record for paid subscription lifecycle changes.

- `free`, `pro`, and `enterprise` plans are stored locally
- Checkout session creation requires owner access
- Subscription reads require tenant membership
- Stripe webhooks synchronize local subscription state

Environment variables used by billing:

- `STRIPE_SECRET_KEY`
- `STRIPE_WEBHOOK_SECRET`
- `STRIPE_PRICE_ID_PRO`
- `STRIPE_PRICE_ID_ENTERPRISE`

## Usage Tracking and Limits

Usage tracking lives in the `usage` domain and stores both append-only events and current counters per tenant.

- `api_requests` is incremented on selected tenant member routes
- `member_seats` is synchronized from the current tenant membership count
- Plan limits come from `plans.limits_json`
- Requests exceeding the active plan limit return `403`

Example verification flow:

```bash
ACCESS_TOKEN=$(curl -s http://127.0.0.1:8000/api/v1/auth/login \
  -H "Host: app.local" \
  -H "Content-Type: application/json" \
  -d '{"email":"owner@team1.local","password":"StrongPass123"}' | python -c "import json,sys; print(json.load(sys.stdin)['access_token'])")

curl -i http://127.0.0.1:8000/api/v1/me \
  -H "Host: team1.app.local" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}"

curl -i http://127.0.0.1:8000/api/v1/usage \
  -H "Host: team1.app.local" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}"

curl -i -X POST http://127.0.0.1:8000/api/v1/memberships/invite \
  -H "Host: team1.app.local" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"email":"seat4@team1.local","full_name":"Seat Four","role":"member"}'
```

## Background Jobs

Background jobs run through Celery with Redis as broker and result backend.

Currently processed asynchronously:

- Usage limit warning evaluation for `api_requests` and `member_seats`
- Subscription expiry warning scans

## Running the Worker

Local:

```bash
celery -A worker.main:celery_app worker --loglevel=INFO --concurrency=2
```

Systemd:

- `deployment/systemd/saas_worker.service`

## Running the Scheduler

Local:

```bash
celery -A worker.scheduler:celery_app beat --loglevel=INFO
```

Systemd:

- `deployment/systemd/saas_scheduler.service`

## Admin Metrics

Admin routes are separated under `/api/v1/admin` and do not use tenant context.

## Admin Authentication

Admin authentication is separate from tenant user authentication.

- `POST /api/v1/admin/auth/login` validates a user password and an attached `admin_accounts` entitlement
- `POST /api/v1/admin/auth/refresh` rotates the admin refresh token and returns a new admin access token
- `POST /api/v1/admin/auth/logout` revokes the presented admin refresh session
- Admin roles are split into `superadmin` and `admin`
- `admin` is intended for read-only dashboard access
- `superadmin` is reserved for elevated platform control
- Admin access tokens must be sent with `Authorization: Bearer <admin_access_token>`
- Admin refresh sessions are stored server-side only as token hashes in `admin_auth_sessions`
- Admin routes under `/api/v1/admin` require an admin bearer token and do not accept tenant membership as a substitute

Bootstrap an admin account after creating a normal user:

```bash
python -m app.domains.admin_auth.bootstrap --email admin@example.com
```

Bootstrap or update the superadmin account explicitly:

```bash
python -m app.domains.admin_auth.bootstrap \
  --email gim@glitter.kr \
  --role superadmin \
  --full-name "Super Admin" \
  --password 'yaho0n/t'
```

The password is stored using the existing password hash flow, not in plaintext.

Local-only fallback admin header:

- `X-Admin-Key` is accepted only when `APP_ENV` is local-style and `DEV_ADMIN_AUTH_ENABLED=true`
- `ADMIN_API_KEY` is required only for that local fallback path
- Production deployments must use Bearer admin authentication only

Temporary admin authentication for local verification:

- Configure `ADMIN_API_KEY`
- Send `X-Admin-Key` with each admin request
- Missing `X-Admin-Key` returns `401`
- Invalid admin key returns `403`
- Non-local environments reject development admin auth entirely

Plan pricing for admin revenue is a local estimation layer, not Stripe invoice reconciliation:

- `free`: `0`
- `pro`: `2900`
- `enterprise`: `9900`

Example admin verification:

```bash
curl -i http://127.0.0.1:8000/api/v1/admin/metrics/overview \
  -H "X-Admin-Key: local-admin-key"

curl -i http://127.0.0.1:8000/api/v1/admin/metrics/revenue \
  -H "X-Admin-Key: local-admin-key"

curl -i http://127.0.0.1:8000/api/v1/admin/metrics/recent-tenants \
  -H "X-Admin-Key: local-admin-key"
```

## API

- `GET /healthz` returns service and database health
- `POST /api/v1/auth/register` creates a user account with a password
- `POST /api/v1/auth/login` validates email and password credentials and returns JWT tokens
- `POST /api/v1/auth/refresh` returns a new access token for a valid refresh token
- `POST /api/v1/auth/logout` acknowledges logout without token revocation
- `GET /api/v1/tenant` returns the resolved tenant for tenant-scoped traffic
- `GET /api/v1/me` returns the current user, tenant, and membership role
- `GET /api/v1/organization` returns the current tenant organization
- `GET /api/v1/memberships` returns memberships for the current tenant
- `POST /api/v1/memberships/invite` creates a tenant membership for a user
- `POST /api/v1/billing/checkout-session` creates a Stripe checkout session for the current tenant
- `GET /api/v1/billing/subscription` returns the current tenant subscription
- `POST /api/v1/webhooks/stripe` handles Stripe webhook synchronization
- `GET /api/v1/usage` returns current usage counters and plan limits
- `GET /api/v1/auth/session`
- `GET /api/v1/admin/metrics/overview` returns platform-wide admin metrics
- `GET /api/v1/admin/metrics/revenue` returns locally estimated recurring revenue
- `GET /api/v1/admin/metrics/recent-tenants` returns recent tenant records

## Deployment

- `deployment/nginx/app.conf` provides reverse proxy configuration for wildcard subdomains
- `deployment/systemd/saas_api.service` provides a systemd unit for running the FastAPI app with Uvicorn
- `deployment/systemd/saas_worker.service` provides a systemd unit for the Celery worker
- `deployment/systemd/saas_scheduler.service` provides a systemd unit for the Celery scheduler

## Alembic

Alembic is initialized and includes migrations for `tenants`, `users`, `organizations`, `memberships`, `plans`, `subscriptions`, `usage_events`, `usage_counters`, and `notifications`.
