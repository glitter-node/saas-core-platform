import smtplib
import ssl
from email.message import EmailMessage

from app.config.settings import Settings
from app.config.settings import get_settings


VALID_MAIL_ENCRYPTION = {"none", "tls", "ssl"}


def build_email_message(
    *,
    to_address: str,
    subject: str,
    body: str,
    html_body: str | None = None,
    settings: Settings | None = None,
) -> EmailMessage:
    runtime_settings = settings or get_settings()
    message = EmailMessage()
    message["From"] = f"{runtime_settings.mail_from_name} <{runtime_settings.mail_from_address}>"
    message["To"] = to_address
    message["Subject"] = subject
    message.set_content(body)
    if html_body is not None:
        message.add_alternative(html_body, subtype="html")
    return message


def verify_mail_settings(settings: Settings | None = None) -> None:
    runtime_settings = settings or get_settings()
    if runtime_settings.mail_mailer.strip().lower() != "smtp":
        raise ValueError("MAIL_MAILER must be smtp")
    if runtime_settings.mail_encryption.strip().lower() not in VALID_MAIL_ENCRYPTION:
        raise ValueError("MAIL_ENCRYPTION must be one of: none, tls, ssl")
    required_values = {
        "MAIL_HOST": runtime_settings.mail_host,
        "MAIL_PORT": str(runtime_settings.mail_port),
        "MAIL_USERNAME": runtime_settings.mail_username,
        "MAIL_FROM_ADDRESS": runtime_settings.mail_from_address,
        "MAIL_FROM_NAME": runtime_settings.mail_from_name,
    }
    missing = [name for name, value in required_values.items() if not value or not value.strip()]
    if missing:
        raise ValueError(f"Missing mail configuration: {', '.join(missing)}")


def open_smtp_connection(settings: Settings | None = None) -> smtplib.SMTP:
    runtime_settings = settings or get_settings()
    verify_mail_settings(runtime_settings)
    encryption = runtime_settings.mail_encryption.strip().lower()
    timeout = 15
    if encryption == "ssl":
        client = smtplib.SMTP_SSL(
            host=runtime_settings.mail_host,
            port=runtime_settings.mail_port,
            timeout=timeout,
            context=ssl.create_default_context(),
        )
    else:
        client = smtplib.SMTP(
            host=runtime_settings.mail_host,
            port=runtime_settings.mail_port,
            timeout=timeout,
        )
    client.ehlo()
    if encryption == "tls":
        client.starttls(context=ssl.create_default_context())
        client.ehlo()
    if runtime_settings.mail_username and runtime_settings.mail_password:
        client.login(runtime_settings.mail_username, runtime_settings.mail_password)
    return client


def verify_smtp_connection(settings: Settings | None = None) -> None:
    client = open_smtp_connection(settings)
    client.quit()


def send_email(
    *,
    to_address: str,
    subject: str,
    body: str,
    html_body: str | None = None,
    settings: Settings | None = None,
) -> None:
    runtime_settings = settings or get_settings()
    message = build_email_message(
        to_address=to_address,
        subject=subject,
        body=body,
        html_body=html_body,
        settings=runtime_settings,
    )
    client = open_smtp_connection(runtime_settings)
    try:
        client.send_message(message)
    finally:
        client.quit()
