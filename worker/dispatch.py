from sqlalchemy.orm import Session

from worker.celery_app import celery_app


def enqueue_task_after_commit(session: Session, task_name: str, *args: object) -> None:
    tasks = session.info.setdefault("deferred_tasks", [])
    tasks.append((task_name, args))


def dispatch_deferred_tasks(session: Session) -> None:
    tasks = session.info.pop("deferred_tasks", [])
    for task_name, args in tasks:
        celery_app.send_task(task_name, args=args)
