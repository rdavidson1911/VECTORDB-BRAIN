from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any
from urllib.parse import urlparse

from devtools.smtp_lab.config import SmtpLabSettings

_ALLOWED_WEB_HOSTS = frozenset({"127.0.0.1", "localhost", "[::1]"})


def _validate_web_base_url(base_url: str) -> None:
    parsed = urlparse(base_url)
    if parsed.scheme != "http":
        raise ValueError(f"MailCatcher web URL must use http (dev only), got {base_url!r}")
    host = (parsed.hostname or "").lower()
    if host not in _ALLOWED_WEB_HOSTS:
        raise ValueError(
            f"MailCatcher web URL must target localhost, got host {host!r} in {base_url!r}"
        )


class MailcatcherApi:
    """Minimal MailCatcher REST client (read + clear mailbox)."""

    def __init__(self, settings: SmtpLabSettings | None = None) -> None:
        self._cfg = settings or SmtpLabSettings.from_env()

    @property
    def web_base_url(self) -> str:
        return self._cfg.web_base_url

    def _urlopen(self, url: str, method: str):
        _validate_web_base_url(self._cfg.web_base_url)
        req = urllib.request.Request(url, method=method)
        return urllib.request.urlopen(  # nosec B310 - http localhost only, validated above
            req,
            timeout=self._cfg.smtp_timeout_seconds,
        )

    def list_messages(self) -> list[dict[str, Any]]:
        url = f"{self._cfg.web_base_url}/messages"
        with self._urlopen(url, "GET") as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if not isinstance(data, list):
            raise TypeError(f"Expected list from {url}, got {type(data)!r}")
        return data

    def clear_all(self) -> None:
        url = f"{self._cfg.web_base_url}/messages"
        try:
            self._urlopen(url, "DELETE").close()
        except urllib.error.HTTPError as exc:
            if exc.code not in (200, 204):
                raise

    def find_by_subject_contains(self, needle: str) -> list[dict[str, Any]]:
        needle_lower = needle.lower()
        return [m for m in self.list_messages() if needle_lower in (m.get("subject") or "").lower()]
