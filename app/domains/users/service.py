from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.domains.auth.passwords import make_unusable_password_hash
from app.domains.auth.passwords import normalize_email
from app.domains.users.models import User


def build_user_by_email_query(email: str) -> Select[tuple[User]]:
    return select(User).where(User.email == normalize_email(email))


def build_user_by_id_query(user_id: int) -> Select[tuple[User]]:
    return select(User).where(User.id == user_id)


def get_user_by_email(session: Session, email: str) -> User | None:
    return session.execute(build_user_by_email_query(email)).scalar_one_or_none()


def get_user_by_id(session: Session, user_id: int) -> User | None:
    return session.execute(build_user_by_id_query(user_id)).scalar_one_or_none()


def create_user(
    session: Session,
    email: str,
    full_name: str,
    password_hash: str | None = None,
    is_active: bool = True,
) -> User:
    user = User(
        email=normalize_email(email),
        full_name=full_name.strip(),
        password_hash=password_hash or make_unusable_password_hash(),
        is_active=is_active,
    )
    session.add(user)
    session.flush()
    return user
