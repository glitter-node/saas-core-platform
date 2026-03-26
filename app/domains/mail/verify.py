import argparse

from app.domains.mail.service import send_email
from app.domains.mail.service import verify_smtp_connection


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--send-test", action="store_true")
    parser.add_argument("--to")
    args = parser.parse_args()

    verify_smtp_connection()
    print("SMTP connection verified")

    if not args.send_test:
        return
    if not args.to:
        raise ValueError("--to is required when --send-test is used")

    send_email(
        to_address=args.to,
        subject="SMTP verification",
        body="SMTP verification succeeded.",
    )
    print(f"Test email sent to {args.to}")


if __name__ == "__main__":
    main()
