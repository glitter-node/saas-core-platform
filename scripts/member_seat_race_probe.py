import http.client
import json
import threading
from pathlib import Path
import sys

from sqlalchemy import select, text

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import models
from app.db.session import SessionLocal
from app.domains.auth.passwords import hash_password
from app.domains.memberships.models import Membership, MembershipRole
from app.domains.memberships.service import create_membership, get_membership_by_tenant_and_user
from app.domains.subscriptions.service import get_plan_by_code, get_subscription_by_tenant
from app.domains.tenants.models import Tenant
from app.domains.users.models import User
from app.domains.users.service import create_user, get_user_by_email


API_HOST = "127.0.0.1"
API_PORT = 18010
ROOT_HOST = "app.local"
TENANT_HOST = "team-a.app.local"
OWNER_EMAIL = "owner-a@test.local"
OWNER_PASSWORD = "StrongPass123"
OUTSIDER_EMAIL = "outsider@test.local"
RACE_EMAILS = ("race_a@test.local", "race_b@test.local")
LOG_PATH = Path("/tmp/saas_validation_api.log")
ITERATIONS = 10


def _sql_rows(session, sql: str) -> list[tuple]:
    return list(session.execute(text(sql)).all())


def _render_rows(rows: list[tuple]) -> list[list]:
    rendered = []
    for row in rows:
        rendered.append([value.isoformat() if hasattr(value, "isoformat") else value for value in row])
    return rendered


def _ensure_user(session, email: str, full_name: str, password: str) -> User:
    user = get_user_by_email(session, email)
    if user is None:
        user = create_user(
            session=session,
            email=email,
            full_name=full_name,
            password_hash=hash_password(password),
            is_active=True,
        )
    else:
        user.full_name = full_name
        user.password_hash = hash_password(password)
        user.is_active = True
        session.add(user)
    return user


def reset_preconditions() -> dict[str, object]:
    with SessionLocal() as session:
        tenant = session.execute(select(Tenant).where(Tenant.slug == "team-a")).scalar_one()
        free_plan = get_plan_by_code(session, "free")
        if free_plan is None:
            raise RuntimeError("free plan not found")
        subscription = get_subscription_by_tenant(session, tenant.id)
        if subscription is None:
            raise RuntimeError("team-a subscription not found")
        subscription.plan = free_plan
        session.add(subscription)

        owner = get_user_by_email(session, OWNER_EMAIL)
        if owner is None:
            raise RuntimeError("owner-a@test.local not found")

        outsider = _ensure_user(session, OUTSIDER_EMAIL, "Outsider", OWNER_PASSWORD)

        for email in RACE_EMAILS + ("seat3@test.local",):
            user = get_user_by_email(session, email)
            if user is None:
                continue
            memberships = session.execute(select(Membership).where(Membership.user_id == user.id)).scalars().all()
            for membership in memberships:
                session.delete(membership)
            session.flush()
            session.delete(user)

        memberships = session.execute(select(Membership).where(Membership.tenant_id == tenant.id)).scalars().all()
        for membership in memberships:
            if membership.user_id not in {owner.id, outsider.id}:
                session.delete(membership)
        session.flush()

        owner_membership = get_membership_by_tenant_and_user(session, tenant.id, owner.id)
        if owner_membership is None:
            create_membership(session, tenant.id, owner, MembershipRole.owner)
        else:
            owner_membership.role = MembershipRole.owner
            session.add(owner_membership)

        outsider_membership = get_membership_by_tenant_and_user(session, tenant.id, outsider.id)
        if outsider_membership is None:
            create_membership(session, tenant.id, outsider, MembershipRole.member)
        else:
            outsider_membership.role = MembershipRole.member
            session.add(outsider_membership)

        session.commit()

    return collect_db_state()


def collect_db_state() -> dict[str, object]:
    with SessionLocal() as session:
        queries = {
            "team_plan": """
                SELECT t.slug, p.code, JSON_EXTRACT(p.limits_json, '$.member_seats') AS member_seats
                FROM subscriptions s
                JOIN tenants t ON t.id=s.tenant_id
                JOIN plans p ON p.id=s.plan_id
                WHERE t.slug='team-a'
            """,
            "team_memberships": """
                SELECT u.email, m.role
                FROM memberships m
                JOIN users u ON u.id=m.user_id
                JOIN tenants t ON t.id=m.tenant_id
                WHERE t.slug='team-a'
                ORDER BY m.id
            """,
            "team_member_count": """
                SELECT COUNT(*)
                FROM memberships m
                JOIN tenants t ON t.id=m.tenant_id
                WHERE t.slug='team-a'
            """,
            "race_users": """
                SELECT id, email, is_active
                FROM users
                WHERE email IN ('race_a@test.local','race_b@test.local')
                ORDER BY email
            """,
            "race_memberships": """
                SELECT u.email, t.slug, m.role
                FROM memberships m
                JOIN users u ON u.id=m.user_id
                JOIN tenants t ON t.id=m.tenant_id
                WHERE u.email IN ('race_a@test.local','race_b@test.local')
                ORDER BY u.email, t.slug
            """,
        }
        return {name: _render_rows(_sql_rows(session, sql)) for name, sql in queries.items()}


def login_owner() -> tuple[str, str]:
    body = json.dumps({"email": OWNER_EMAIL, "password": OWNER_PASSWORD})
    response = request("POST", "/api/v1/auth/login", ROOT_HOST, body, {"Content-Type": "application/json"})
    payload = json.loads(response["body"])
    return payload["access_token"], response["raw"]


def request(method: str, path: str, host: str, body: str | None = None, headers: dict[str, str] | None = None) -> dict[str, object]:
    conn = http.client.HTTPConnection(API_HOST, API_PORT, timeout=10)
    actual_headers = {"Host": host}
    if headers:
        actual_headers.update(headers)
    conn.request(method, path, body=body, headers=actual_headers)
    response = conn.getresponse()
    payload = response.read()
    header_lines = "".join(f"{key}: {value}\r\n" for key, value in response.getheaders())
    raw = f"HTTP/1.1 {response.status} {response.reason}\r\n{header_lines}\r\n{payload.decode()}"
    conn.close()
    return {"status": response.status, "reason": response.reason, "body": payload.decode(), "raw": raw}


def invite_worker(email: str, full_name: str, token: str, barrier: threading.Barrier, results: dict[str, dict[str, object]]) -> None:
    barrier.wait()
    results[email] = request(
        "POST",
        "/api/v1/memberships/invite",
        TENANT_HOST,
        json.dumps({"email": email, "full_name": full_name, "role": "member"}),
        {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )


def run_iteration(iteration: int) -> dict[str, object]:
    before = reset_preconditions()
    log_before = LOG_PATH.read_text().splitlines()
    token, login_raw = login_owner()
    barrier = threading.Barrier(2)
    results: dict[str, dict[str, object]] = {}
    threads = [
        threading.Thread(target=invite_worker, args=(RACE_EMAILS[0], "Race A", token, barrier, results)),
        threading.Thread(target=invite_worker, args=(RACE_EMAILS[1], "Race B", token, barrier, results)),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    after = collect_db_state()
    log_after = LOG_PATH.read_text().splitlines()
    statuses = sorted(result["status"] for result in results.values())
    final_count = after["team_member_count"][0][0]
    race_membership_count = len(after["race_memberships"])
    if statuses == [201, 403] and final_count == 3 and race_membership_count == 1:
        verdict = "SAFE"
    elif statuses == [201, 201] or final_count > 3 or race_membership_count > 1:
        verdict = "BROKEN"
    else:
        verdict = "INCONCLUSIVE"
    return {
        "iteration": iteration,
        "login_raw": login_raw,
        "responses": {email: results[email]["raw"] for email in RACE_EMAILS},
        "before": before,
        "after": after,
        "new_log_lines": log_after[len(log_before):],
        "verdict": verdict,
    }


def main() -> None:
    iterations = []
    final_verdict = "SAFE"
    for index in range(1, ITERATIONS + 1):
        iteration = run_iteration(index)
        iterations.append(iteration)
        if iteration["verdict"] == "BROKEN":
            final_verdict = "BROKEN"
            break
        if iteration["verdict"] == "INCONCLUSIVE":
            final_verdict = "INCONCLUSIVE"
    report = {
        "api_base": f"http://{API_HOST}:{API_PORT}",
        "tenant_host": TENANT_HOST,
        "iterations_requested": ITERATIONS,
        "iterations_ran": len(iterations),
        "final_verdict": final_verdict,
        "iterations": iterations,
    }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
