from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy import event
from sqlalchemy.orm import Session, sessionmaker

from app.config.settings import get_settings
from worker.dispatch import dispatch_deferred_tasks

settings = get_settings()

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)


@event.listens_for(Session, "after_commit")
def on_after_commit(session: Session) -> None:
    dispatch_deferred_tasks(session)


@event.listens_for(Session, "after_rollback")
def on_after_rollback(session: Session) -> None:
    session.info.pop("deferred_tasks", None)


def get_db_session() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
