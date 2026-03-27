# Operations Manual

Canonical production target:

- Ubuntu 24.04 LTS
- install path: `/srv/multi_tenant_saas_subscription_platform`
- systemd services: `saas_api`, `saas_worker`, `saas_scheduler`
- reverse proxy: nginx

## Health Checks

Application health:

```bash
APP_DOMAIN=$(awk -F= '$1=="APP_DOMAIN"{print $2}' /srv/multi_tenant_saas_subscription_platform/.env | tr -d '"')
curl -i -H "Host: ${APP_DOMAIN}" http://127.0.0.1/healthz
```

Expected healthy response:

- HTTP `200`
- JSON includes:
  - `"status":"ok"`
  - `"checks":{"database":"ok","redis":"ok"}`

If the API is running but a dependency is down, `/healthz` returns HTTP `503`.

Full operator status snapshot:

```bash
sudo /srv/multi_tenant_saas_subscription_platform/scripts/ops_status.sh
```

## Log Locations

- API log: `/var/log/multi_tenant_saas_subscription_platform/api.log`
- Worker log: `/var/log/multi_tenant_saas_subscription_platform/worker.log`
- Scheduler log: `/var/log/multi_tenant_saas_subscription_platform/scheduler.log`
- Nginx access log: `/var/log/nginx/access.log`
- Nginx error log: `/var/log/nginx/error.log`

Systemd journal is also available for each service:

```bash
sudo journalctl -u saas_api -u saas_worker -u saas_scheduler -n 100 --no-pager
```

## Log Inspection

Tail logs:

```bash
sudo tail -f /var/log/multi_tenant_saas_subscription_platform/api.log
sudo tail -f /var/log/multi_tenant_saas_subscription_platform/worker.log
sudo tail -f /var/log/multi_tenant_saas_subscription_platform/scheduler.log
sudo tail -f /var/log/nginx/error.log
```

Recent errors:

```bash
sudo grep -iE 'error|exception|traceback|failed' /var/log/multi_tenant_saas_subscription_platform/api.log /var/log/multi_tenant_saas_subscription_platform/worker.log /var/log/multi_tenant_saas_subscription_platform/scheduler.log /var/log/nginx/error.log | tail -n 100
```

Recent request failures:

```bash
sudo tail -n 100 /var/log/nginx/access.log
sudo tail -n 100 /var/log/multi_tenant_saas_subscription_platform/api.log
```

## Failure Isolation

API down:

- Detect:
```bash
sudo systemctl status saas_api --no-pager
curl -i -H "Host: ${APP_DOMAIN}" http://127.0.0.1/healthz
```
- Recover:
```bash
sudo systemctl restart saas_api
```

Worker down:

- Detect:
```bash
sudo systemctl status saas_worker --no-pager
redis-cli LLEN operations
sudo tail -n 100 /var/log/multi_tenant_saas_subscription_platform/worker.log
```
- Recover:
```bash
sudo systemctl restart saas_worker
```

Scheduler down:

- Detect:
```bash
sudo systemctl status saas_scheduler --no-pager
sudo tail -n 100 /var/log/multi_tenant_saas_subscription_platform/scheduler.log
```
- Recover:
```bash
sudo systemctl restart saas_scheduler
```

Redis down:

- Detect:
```bash
sudo systemctl status redis-server --no-pager
curl -i -H "Host: ${APP_DOMAIN}" http://127.0.0.1/healthz
sudo tail -n 100 /var/log/multi_tenant_saas_subscription_platform/worker.log
```
- Recovery:
```bash
sudo systemctl restart redis-server
sudo systemctl restart saas_worker saas_scheduler
```

Database down:

- Detect:
```bash
sudo systemctl status mariadb --no-pager
curl -i -H "Host: ${APP_DOMAIN}" http://127.0.0.1/healthz
sudo tail -n 100 /var/log/multi_tenant_saas_subscription_platform/api.log
```
- Recovery:
```bash
sudo systemctl restart mariadb
sudo systemctl restart saas_api saas_worker saas_scheduler
```

## Safe Restarts

Restart one service:

```bash
sudo systemctl restart saas_api
sudo systemctl restart saas_worker
sudo systemctl restart saas_scheduler
```

Restart all application services safely:

```bash
sudo systemctl restart saas_api saas_worker saas_scheduler
```

Restart reverse proxy:

```bash
sudo nginx -t -c /srv/multi_tenant_saas_subscription_platform/deployment/nginx/nginx.conf
sudo systemctl restart nginx
```

## Background Task Observability

Queue depth:

```bash
redis-cli LLEN operations
```

Worker task processing:

```bash
sudo tail -n 100 /var/log/multi_tenant_saas_subscription_platform/worker.log
```

Scheduler activity:

```bash
sudo tail -n 100 /var/log/multi_tenant_saas_subscription_platform/scheduler.log
```

Validation path for API + queue + worker side effect:

```bash
sudo /srv/multi_tenant_saas_subscription_platform/scripts/validate_production.sh
```

Automatic recovery validation:

```bash
sudo /srv/multi_tenant_saas_subscription_platform/scripts/test_auto_recovery.sh
```

## Minimal Alert Signals

- Health endpoint failure:
```bash
curl -fsS -H "Host: ${APP_DOMAIN}" http://127.0.0.1/healthz >/dev/null || echo "healthz failed"
```

- Repeated worker errors:
```bash
sudo grep -ciE 'error|exception|traceback|failed' /var/log/multi_tenant_saas_subscription_platform/worker.log
```

- Queue backlog growth:
```bash
redis-cli LLEN operations
```

## Recovery Signals

Worker reconnect:

- `consumer: Cannot connect to redis://`
- `Trying again in`
- `Connected to redis://`
- `Task worker.check_usage_limit_warning`

Scheduler recovery:

- `beat: Starting`
- `Removing corrupted schedule file`

API dependency failure:

- `/healthz` returns HTTP `503`
- body contains `"checks":{"database":"error"...}` or `"checks":{"redis":"error"...}`

## Failure Test Procedure

```bash
sudo /srv/multi_tenant_saas_subscription_platform/scripts/test_auto_recovery.sh
```

This script:

- kills `saas_api`, `saas_worker`, and `saas_scheduler` with `SIGKILL`
- waits for systemd to restart each service automatically
- stops Redis and waits for `/healthz` to return `503`
- starts Redis and waits for `/healthz` to return `200`
- stops MariaDB and waits for `/healthz` to return `503`
- starts MariaDB and waits for `/healthz` to return `200`
