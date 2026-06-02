from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SmtpLabSettings:
    """Endpoints for MailCatcher on localhost (dev only)."""

    smtp_host: str = "127.0.0.1"
    smtp_port: int = 1025
    web_base_url: str = "http://127.0.0.1:1081"
    smtp_timeout_seconds: float = 10.0

    @classmethod
    def from_env(cls) -> SmtpLabSettings:
        web = os.environ.get("MAILCATCHER_WEB", "http://127.0.0.1:1081").rstrip("/")
        return cls(
            smtp_host=os.environ.get("SMTP_HOST", "127.0.0.1"),
            smtp_port=int(
                os.environ.get("SMTP_PORT", os.environ.get("MAILCATCHER_SMTP_PORT", "1025"))
            ),
            web_base_url=web,
            smtp_timeout_seconds=float(os.environ.get("SMTP_LAB_TIMEOUT", "10")),
        )
