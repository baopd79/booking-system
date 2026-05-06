from email.message import EmailMessage
from typing import Protocol

import aiosmtplib

from app.core.config import settings


class EmailService(Protocol):
    async def send_verification_email(self, to_email: str, token: str) -> None:
        """Send a verification token to a newly registered customer."""


class SmtpOrLogEmailService:
    """
    Email strategy for MVP.

    If SMTP credentials are configured, send through SMTP. Otherwise log the
    verification token so local development and Postman flows remain usable.
    """

    async def send_verification_email(self, to_email: str, token: str) -> None:
        if not settings.smtp_host or not settings.smtp_user or not settings.smtp_password:
            print(f"[auth.email] verification token for {to_email}: {token}")
            return

        message = EmailMessage()
        message["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
        message["To"] = to_email
        message["Subject"] = "Verify your Booking System email"
        message.set_content(
            "Welcome to Booking System.\n\n"
            f"Use this token to verify your email: {token}\n\n"
            "This token expires in 24 hours."
        )

        await aiosmtplib.send(
            message,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user,
            password=settings.smtp_password,
            start_tls=True,
        )


def get_email_service() -> EmailService:
    return SmtpOrLogEmailService()
