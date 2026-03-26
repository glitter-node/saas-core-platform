from worker.celery_app import celery_app
from worker import tasks


def main() -> None:
    celery_app.start()


if __name__ == "__main__":
    main()
