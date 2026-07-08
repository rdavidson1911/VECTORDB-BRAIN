from __future__ import annotations

import socket

from devtools.smtp_lab.config import SmtpLabSettings


def smtp_reachable(settings: SmtpLabSettings | None = None) -> bool:
    """Return True if something accepts TCP on the configured SMTP port."""
    cfg = settings or SmtpLabSettings.from_env()
    try:
        with socket.create_connection((cfg.smtp_host, cfg.smtp_port), timeout=2.0):
            return True
    except OSError:
        return False
