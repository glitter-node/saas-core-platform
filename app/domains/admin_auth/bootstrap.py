import argparse

from sqlalchemy.orm import Session

from app.db import models as db_models
from app.db.session import SessionLocal
from app.domains.admin_auth.models import AdminAccount
from app.domains.admin_auth.models import AdminRole
from app.domains.auth.passwords import hash_password
from app.domains.users.service import get_user_by_email
from app.domains.users.service import create_user


def create_admin_account(
    session: Session,
    email: str,
    bootstrap_source: str = "cli",
    role: AdminRole = AdminRole.admin,
    full_name: str | None = None,
    password: str | None = None,
) -> AdminAccount:
    user = get_user_by_email(session, email)
    if user is None:
        if not full_name or not password:
            raise ValueError("full_name and password are required when creating a new superadmin user")
        user = create_user(
            session=session,
            email=email,
            full_name=full_name,
            password_hash=hash_password(password),
            is_active=True,
        )
    elif password:
        user.password_hash = hash_password(password)
        user.is_active = True
        session.add(user)

    admin_account = user.admin_account
    if admin_account is None:
        admin_account = AdminAccount(user_id=user.id, role=role, bootstrap_source=bootstrap_source)
        session.add(admin_account)
    else:
        admin_account.role = role
        admin_account.bootstrap_source = bootstrap_source
        admin_account.is_active = True
        session.add(admin_account)
    session.commit()
    session.refresh(admin_account)
    return admin_account


def main() -> None:
    _ = db_models
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True)
    parser.add_argument("--bootstrap-source", default="cli")
    parser.add_argument("--role", choices=[AdminRole.admin.value, AdminRole.superadmin.value], default=AdminRole.admin.value)
    parser.add_argument("--full-name", default=None)
    parser.add_argument("--password", default=None)
    args = parser.parse_args()

    session = SessionLocal()
    try:
        admin_account = create_admin_account(
            session,
            args.email,
            args.bootstrap_source,
            AdminRole(args.role),
            args.full_name,
            args.password,
        )
    finally:
        session.close()
    print(f"Created admin account {admin_account.id} for {args.email}")


if __name__ == "__main__":
    main()
