# multi_tenant_saas_subscription_platform

FastAPI backend for a multi-tenant SaaS platform with tenant resolution from the `Host` header, SQLAlchemy 2.x, Alembic migrations, Celery background jobs, and deployment templates for Nginx and systemd.

## Fresh Machine Reproduction

Canonical target: Ubuntu with outbound HTTPS access to PyPI and `sudo` available.

1. Install OS packages and start local MariaDB and Redis:

```bash
./scripts/bootstrap_ubuntu.sh
```

2. Create the Python virtual environment and install Python dependencies:

```bash
./scripts/bootstrap_python.sh
```

3. Create the application environment file:

```bash
cp .env.example .env
```

4. Create the local database and application database user from `DATABASE_URL` in `.env`:

```bash
./scripts/init_local_db.sh
```

5. Run migrations, create deterministic local validation data, and render deployment artifacts:

```bash
.venv/bin/alembic upgrade head
.venv/bin/python scripts/bootstrap_local_data.py
.venv/bin/python scripts/render_deployment.py
```

6. Start the API, worker, and scheduler:

```bash
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
.venv/bin/celery -A worker.main:celery_app worker --loglevel=INFO --concurrency=1 -P solo
.venv/bin/celery -A worker.scheduler:celery_app beat --loglevel=INFO --schedule .local/celerybeat-schedule
```

7. Run the deterministic end-to-end verification:

```bash
APP_PORT=8000 ./scripts/verify_local.sh
```

8. Validate deployment artifacts derived from the clone path:

```bash
nginx -t -c deployment/rendered/nginx/nginx.conf
systemd-analyze verify deployment/rendered/systemd/saas_api.service deployment/rendered/systemd/saas_worker.service deployment/rendered/systemd/saas_scheduler.service
```

## Production Deployment

Canonical production target:

- Ubuntu 24.04 LTS
- install path: `/srv/multi_tenant_saas_subscription_platform`
- process model: `uvicorn` API, Celery worker, Celery beat scheduler
- service manager: systemd
- reverse proxy: nginx on port `80`

Provision the server:

```bash
./scripts/bootstrap_ubuntu.sh
```

Deploy the repository into the canonical production path and install Python dependencies:

```bash
./scripts/deploy_production.sh
```

Create the production environment file:

```bash
sudo cp /srv/multi_tenant_saas_subscription_platform/.env.production.example /srv/multi_tenant_saas_subscription_platform/.env
sudoedit /srv/multi_tenant_saas_subscription_platform/.env
```

Create the database from `DATABASE_URL` in `/srv/multi_tenant_saas_subscription_platform/.env`:

```bash
sudo /srv/multi_tenant_saas_subscription_platform/scripts/init_production_db.sh
```

Run migrations and prepare deterministic validation data:

```bash
sudo /srv/multi_tenant_saas_subscription_platform/.venv/bin/alembic -c /srv/multi_tenant_saas_subscription_platform/alembic.ini upgrade head
sudo /srv/multi_tenant_saas_subscription_platform/scripts/bootstrap_validation_data.sh
```

Enable and start services:

```bash
sudo systemctl enable --now saas_api saas_worker saas_scheduler
sudo nginx -t -c /srv/multi_tenant_saas_subscription_platform/deployment/nginx/nginx.conf
sudo systemctl restart nginx
```

Validate the deployed system:

```bash
sudo systemd-analyze verify /srv/multi_tenant_saas_subscription_platform/deployment/systemd/saas_api.service /srv/multi_tenant_saas_subscription_platform/deployment/systemd/saas_worker.service /srv/multi_tenant_saas_subscription_platform/deployment/systemd/saas_scheduler.service
sudo /srv/multi_tenant_saas_subscription_platform/scripts/validate_production.sh
```

## Architecture

The repository has three runtime areas:

- `app/`: FastAPI application, API routers, middleware, settings, database integration, domain modules, and web pages
- `worker/`: Celery application, worker tasks, and scheduler entrypoints
- `deployment/`: Nginx and systemd deployment templates

The FastAPI application is initialized in `app.main:app`. It:

- loads settings from `app.config.settings`
- creates the FastAPI app
- enables `/docs`, `/redoc`, and `/openapi.json` only when `settings.docs_enabled` is true
- applies `TrustedHostMiddleware`, `CORSMiddleware`, and `TenantContextMiddleware`
- mounts static files from `app/web/static` at `/static`
- includes the API router under `/api/v1`
- includes the web router for landing/login/dashboard pages
- exposes `GET /healthz`

## API Structure

API routes are assembled in `app/api/router.py` and split into three scopes:

- Public routes
  - `/api/v1/auth/*`
  - `/api/v1/admin/auth/*`
  - `/api/v1/webhooks/stripe`
- Tenant routes
  - `/api/v1/tenant`
  - `/api/v1/me`
  - `/api/v1/auth/session`
  - `/api/v1/organization`
  - `/api/v1/memberships`
  - `/api/v1/billing/*`
  - `/api/v1/usage`
- Admin routes
  - `/api/v1/admin`
  - `/api/v1/admin/metrics/*`

Tenant-scoped routers require tenant context. If tenant context is missing, the request fails with `404 Tenant context not found`.

## Tenant Resolution

Tenant resolution is implemented by `TenantContextMiddleware` in `app/middleware/tenant_context.py`.

- The middleware reads the incoming `Host` header
- It compares the host against `APP_DOMAIN`
- If the host is exactly `APP_DOMAIN`, no tenant is resolved
- If the host ends with `.<APP_DOMAIN>`, the prefix before that suffix is treated as the tenant subdomain
- The middleware loads the active tenant by subdomain and stores it in `request.state.tenant`
- If the tenant is not found or inactive, tenant state remains unset

Example with `APP_DOMAIN=app.local`:

- `app.local` -> no tenant context
- `team1.app.local` -> tenant subdomain `team1`

## Web Routes

The web router in `app/web/router.py` serves these routes:

- `GET /` -> `app/web/pages/landing.html`
- `GET /login` -> `app/web/pages/user_login.html`
- `GET /dashboard` -> `app/web/pages/user_dashboard.html`
- `GET /magic-link/complete` -> `app/web/pages/magic_link_complete.html`
- `GET /admin/login` -> `app/web/pages/admin_login.html`
- `GET /admin/dashboard` -> `app/web/pages/admin_dashboard.html`
- `GET /admin/workspaces/new`
- `POST /admin/workspaces`
- `POST /admin/workspaces/{workspace_id}/delete`
- `GET /web-config.js`

The router also exposes:

- `GET /favicon.ico`
- `HEAD /favicon.ico`
- `GET /robots.txt`
- `HEAD /robots.txt`
- `GET /sitemap.xml`
- `HEAD /sitemap.xml`

These three assets are served from absolute filesystem paths outside the repository:

- `/volume1/hwi/gimg/favicon/favicon.ico`
- `/volume1/hwi/saasapi.glitter.kr_robots.txt`
- `/volume1/hwi/saasapi.glitter.kr_sitemap.xml`

If those files do not exist, the route returns `404`.

## Data Model

SQLAlchemy models are registered in `app/db/models.py`. The registered domains are:

- tenants
- organizations
- users
- memberships
- subscriptions and plans
- usage events and usage counters
- notifications
- auth sessions
- auth magic links
- admin accounts
- admin auth sessions
- admin audit logs
- billing event ledger

Alembic migrations in `alembic/versions/` create and evolve these tables.

## Setup

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy the environment file:

```bash
cp .env.example .env
```

4. Configure the required values in `.env`.
5. Run migrations:

```bash
alembic upgrade head
```

6. Start the API:

```bash
uvicorn app.main:app --host 0.0.0.0 --port "${APP_PORT:-8000}"
```

## Environment

Configuration is loaded by `app.config.settings.Settings` from `.env`.

Core variables in `.env.example`:

- `APP_NAME`
- `APP_ENV`
- `APP_PORT`
- `APP_DOMAIN`
- `APP_DEBUG`
- `ENABLE_DOCS`
- `DEV_AUTH_ENABLED`
- `DEV_ADMIN_AUTH_ENABLED`
- `ALLOWED_HOSTS`
- `CORS_ALLOWED_ORIGINS`
- `DATABASE_URL`
- `REDIS_URL`
- `SECRET_KEY`
- `ACCESS_TOKEN_EXPIRE_MINUTES`
- `REFRESH_TOKEN_EXPIRE_DAYS`
- `MAGIC_LINK_EXPIRE_MINUTES`
- `ADMIN_ACCESS_TOKEN_EXPIRE_MINUTES`
- `ADMIN_REFRESH_TOKEN_EXPIRE_DAYS`
- `JWT_ALGORITHM`
- `ADMIN_JWT_SCOPE`
- `MAIL_MAILER`
- `MAIL_HOST`
- `MAIL_PORT`
- `MAIL_USERNAME`
- `MAIL_PASSWORD`
- `MAIL_ENCRYPTION`
- `MAIL_FROM_ADDRESS`
- `MAIL_FROM_NAME`
- `STRIPE_SECRET_KEY`
- `STRIPE_WEBHOOK_SECRET`
- `STRIPE_PRICE_ID_PRO`
- `STRIPE_PRICE_ID_ENTERPRISE`
- `SUBSCRIPTION_EXPIRY_WARNING_DAYS`
- `USAGE_WARNING_THRESHOLD_PERCENT`
- `SCHEDULER_SUBSCRIPTION_EXPIRY_SCAN_MINUTES`
- `ADMIN_API_KEY`

Runtime validation enforced by `app/config/settings.py`:

- non-local environments require `DATABASE_URL`, `SECRET_KEY`, `STRIPE_SECRET_KEY`, and `STRIPE_WEBHOOK_SECRET`
- `APP_DEBUG` must be false outside local environments
- `CORS_ALLOWED_ORIGINS` cannot contain `*` outside local environments
- `JWT_ALGORITHM` must be `HS256`
- `MAIL_MAILER` must be `smtp`
- `MAIL_ENCRYPTION` must be one of `none`, `tls`, or `ssl`
- development auth flags are rejected outside local-style environments
- `ADMIN_API_KEY` is required when `DEV_ADMIN_AUTH_ENABLED=true`

## Authentication

### User Authentication

User auth routes are implemented in `app/domains/auth/router.py`.

- `POST /api/v1/auth/register`
  - creates an active user with normalized email and hashed password
- `POST /api/v1/auth/login`
  - validates email and password
  - updates `last_login_at`
  - returns access and refresh tokens
- `POST /api/v1/auth/discover`
  - checks tenant memberships for the submitted email
  - if exactly one active tenant exists, sends a magic link immediately
  - if multiple active tenants exist, returns those tenants so the client can choose
  - if no active tenant exists, returns example tenants
- `GET /api/v1/auth/tenant-examples`
  - returns active tenant examples
- `POST /api/v1/auth/magic-link/start`
  - resolves tenant context from the request tenant or `tenant_subdomain`
  - sends a tenant-scoped magic link email
- `POST /api/v1/auth/magic-link/consume`
  - validates the magic link
  - creates the user if missing
  - creates a tenant membership with role `member` if missing and within usage limits
  - updates `last_login_at`
  - returns access and refresh tokens
- `POST /api/v1/auth/refresh`
  - rotates the refresh token
  - returns a new refresh token and a new access token
- `POST /api/v1/auth/logout`
  - revokes the presented refresh token
- `GET /api/v1/auth/session`
  - requires tenant context and authenticated user
  - returns `tenant_slug`, `tenant_id`, and `user_id`

Bearer auth behavior is implemented in `app/domains/auth/dependencies.py`:

- authenticated requests use `Authorization: Bearer <access_token>`
- the token subject must match an active user
- if the token is absent and `X-User-Email` is present, local development header auth is used only when `DEV_AUTH_ENABLED=true` and the environment is local-style

Tenant membership checks:

- tenant member access requires an authenticated user who belongs to the resolved tenant
- non-members receive `403 Tenant membership required`
- owner/admin restrictions are enforced for selected routes

### Admin Authentication

Admin auth routes are implemented in `app/domains/admin_auth/router.py`.

- `POST /api/v1/admin/auth/login`
  - validates email and password
  - requires an active admin account for that user
  - if `mfa_enabled` is true and no `otp_code` is supplied, returns `403 MFA code required`
  - if `mfa_enabled` is true and an `otp_code` is supplied, returns `403 MFA verification is not configured`
  - updates user and admin login timestamps
  - returns admin access and refresh tokens
- `POST /api/v1/admin/auth/magic-link/start`
  - looks up the user by email
  - creates the user if missing
  - creates an admin account if missing
  - sends an admin magic link when the user and admin account are active
- `POST /api/v1/admin/auth/magic-link/consume`
  - validates the magic link
  - creates the user if missing
  - creates an admin account if missing
  - updates login timestamps
  - returns admin access and refresh tokens
- `POST /api/v1/admin/auth/refresh`
  - rotates the admin refresh token
  - returns a new admin refresh token and access token
- `POST /api/v1/admin/auth/logout`
  - revokes the presented admin refresh token

Admin route protection is implemented in `app/domains/admin/dependencies.py`:

- admin routes accept `Authorization: Bearer <admin_access_token>`
- admin routes also accept the `saas_admin_access_token` cookie as a bearer token source
- local development fallback accepts `X-Admin-Key` only when `DEV_ADMIN_AUTH_ENABLED=true` in a local-style environment and `ADMIN_API_KEY` matches

Bootstrap command:

```bash
python -m app.domains.admin_auth.bootstrap --email admin@example.com
```

The bootstrap module can also create or update a superadmin account:

```bash
python -m app.domains.admin_auth.bootstrap \
  --email admin@example.com \
  --role superadmin \
  --full-name "Super Admin" \
  --password "StrongPass123"
```

## Tenant Routes

Implemented tenant routes:

- `GET /api/v1/tenant`
  - returns the resolved tenant
- `GET /api/v1/me`
  - requires authenticated tenant membership
  - returns the current user, tenant, and membership role
- `GET /api/v1/organization`
  - returns the organization for the current tenant
- `GET /api/v1/memberships`
  - requires authenticated tenant membership
  - returns memberships for the current tenant
- `POST /api/v1/memberships/invite`
  - requires owner or admin membership
  - creates the user if missing
  - rejects duplicate memberships
  - enforces the `member_seats` usage limit before creating the membership
- `GET /api/v1/usage`
  - requires authenticated tenant membership
  - returns plan, counters, limits, remaining values, and per-metric summaries
- `GET /api/v1/billing/subscription`
  - requires authenticated tenant membership
  - ensures a subscription record exists and returns it
- `POST /api/v1/billing/checkout-session`
  - requires owner membership
  - creates a Stripe checkout session for a billable plan

Usage tracking hooks:

- `GET /api/v1/me`
- `GET /api/v1/memberships`
- `GET /api/v1/billing/subscription`

These routes call `track_api_request_usage` and increment the `api_requests` metric.

## Billing and Stripe

Billing logic is implemented in `app/domains/subscriptions`.

- Stripe client configuration uses:
  - `STRIPE_SECRET_KEY`
  - `STRIPE_WEBHOOK_SECRET`
  - `STRIPE_PRICE_ID_PRO`
  - `STRIPE_PRICE_ID_ENTERPRISE`
- `POST /api/v1/billing/checkout-session`
  - rejects non-billable plans with `400 Plan is not billable`
  - builds success and cancel URLs from the incoming request host and scheme
  - returns the Stripe Checkout URL
- `POST /api/v1/webhooks/stripe`
  - requires the `Stripe-Signature` header
  - validates the webhook signature
  - records webhook event ids in the billing event ledger
  - ignores duplicate webhook events
  - applies:
    - `checkout.session.completed`
    - `customer.subscription.created`
    - `customer.subscription.updated`
    - `customer.subscription.deleted`

## Background Jobs

Celery is configured in `worker/celery_app.py` with Redis as both broker and result backend.

Defined tasks in `worker/tasks.py`:

- `worker.check_usage_limit_warning`
  - creates a usage warning notification for a tenant/metric pair
- `worker.scan_subscription_expiry_warnings`
  - creates subscription expiry notifications for tenants approaching expiry

Deferred task dispatch is implemented in `worker/dispatch.py` and connected in `app/db/session.py`:

- tasks can be queued into `session.info["deferred_tasks"]`
- after a successful SQLAlchemy session commit, `dispatch_deferred_tasks` sends them to Celery
- after rollback, deferred tasks are discarded

## Scheduler

Celery beat scheduling is configured in `worker/celery_app.py`.

Scheduled job:

- `scan-subscription-expiry-warnings`
  - task name: `worker.scan_subscription_expiry_warnings`
  - interval: `max(SCHEDULER_SUBSCRIPTION_EXPIRY_SCAN_MINUTES, 1) * 60` seconds

## Mail

Mail verification CLI:

```bash
python -m app.domains.mail.verify
python -m app.domains.mail.verify --send-test --to you@example.com
```

The command verifies SMTP connectivity and can send a test message.

## Running the Worker

Local:

```bash
celery -A worker.main:celery_app worker --loglevel=INFO --concurrency=2
```

Systemd template:

- `deployment/systemd/saas_worker.service`

## Running the Scheduler

Local:

```bash
celery -A worker.scheduler:celery_app beat --loglevel=INFO
```

Systemd template:

- `deployment/systemd/saas_scheduler.service`

## Admin Routes

Admin routes are implemented in `app/domains/admin/router.py`.

- `GET /api/v1/admin`
  - returns the admin namespace, role, and listed capabilities
- `GET /api/v1/admin/metrics/overview`
- `GET /api/v1/admin/metrics/revenue`
- `GET /api/v1/admin/metrics/recent-tenants`

These routes require admin access. Metrics routes also record admin audit log entries.

## Security

`app/main.py` sets these response headers on all requests:

- `X-Frame-Options: SAMEORIGIN`
- `X-Content-Type-Options: nosniff`
- `X-Permitted-Cross-Domain-Policies: none`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Content-Security-Policy`
- `Permissions-Policy`
- `Cross-Origin-Opener-Policy: same-origin`

`app/main.py` also blocks requests to sensitive path patterns and returns `404` for matched paths.

Secret scanning command:

```bash
gitleaks detect --config .gitleaks.toml --source .
```

`.gitignore` excludes `.env` and `.env.*` except `.env.example`.

## Deployment

Nginx template:

- `deployment/nginx/app.conf`
  - proxies `core.glitter.kr` and `*.core.glitter.kr` to `127.0.0.1:8000`
  - forwards `Host`, `X-Forwarded-Host`, `X-Forwarded-Proto`, `X-Forwarded-For`, and `X-Real-IP`

Systemd templates:

- `deployment/systemd/saas_api.service`
  - runs `uvicorn app.main:app --host 127.0.0.1 --port 8000`
  - uses working directory `/srv/multi_tenant_saas_subscription_platform`
  - loads environment from `/srv/multi_tenant_saas_subscription_platform/.env`
- `deployment/systemd/saas_worker.service`
  - runs `celery -A worker.main:celery_app worker --loglevel=INFO --concurrency=2`
- `deployment/systemd/saas_scheduler.service`
  - runs `celery -A worker.scheduler:celery_app beat --loglevel=INFO`

## Alembic

Alembic is configured with:

- `script_location = alembic`
- `sqlalchemy.url = %(DATABASE_URL)s`

The migration environment imports model metadata from `app.db.base.Base` and `app.db.models`.
