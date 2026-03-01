"""Email alert tool — sends an email via SMTP or logs when SMTP is not configured."""

from __future__ import annotations

import logging
import smtplib
from email.mime.text import MIMEText

from langchain_core.tools import tool

from app.config import settings

logger = logging.getLogger(__name__)


def make_send_alert_tool() -> callable:
    """Create a tool that sends an email alert.

    When SMTP credentials are not configured, the tool logs the alert
    instead of sending an actual email — useful for development and demos.
    """

    @tool
    async def send_alert(subject: str, body: str, recipient: str) -> str:
        """Send an email alert to a recipient.

        Use this when you need to notify someone about findings, such as
        an employee whose active time is below the threshold.

        Args:
            subject: Email subject line.
            body: Email body text.
            recipient: Email address of the recipient.
        """
        if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
            logger.info(
                "SMTP not configured — logging alert instead. "
                "To: %s | Subject: %s | Body: %s",
                recipient,
                subject,
                body,
            )
            return (
                f"Alert logged (SMTP not configured). "
                f"To: {recipient}, Subject: {subject}"
            )

        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = settings.SMTP_USER
        msg["To"] = recipient

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)

        return f"Email sent to {recipient} with subject '{subject}'"

    return send_alert
