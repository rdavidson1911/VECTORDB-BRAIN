from __future__ import annotations

import smtplib
from collections.abc import Callable
from dataclasses import dataclass
from email.message import EmailMessage
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from devtools.smtp_lab.config import SmtpLabSettings

ScenarioFn = Callable[[SmtpLabSettings], str]


@dataclass(frozen=True, slots=True)
class Scenario:
    """One teachable SMTP exercise."""

    id: str
    title: str
    description: str
    subject_marker: str
    run: ScenarioFn


def _send(msg: EmailMessage | MIMEMultipart, settings: SmtpLabSettings) -> None:
    with smtplib.SMTP(
        settings.smtp_host, settings.smtp_port, timeout=settings.smtp_timeout_seconds
    ) as smtp:
        smtp.send_message(msg)


def _scenario_plain(settings: SmtpLabSettings) -> str:
    marker = "[smtp-lab:plain]"
    msg = EmailMessage()
    msg["Subject"] = f"{marker} Plain text only"
    msg["From"] = "lab-sender@localhost"
    msg["To"] = "lab-recipient@localhost"
    msg.set_content("Hello from smtp_lab.\n\nThis is a single text/plain body.")
    _send(msg, settings)
    return marker


def _scenario_html(settings: SmtpLabSettings) -> str:
    marker = "[smtp-lab:html]"
    msg = EmailMessage()
    msg["Subject"] = f"{marker} HTML body"
    msg["From"] = "lab-sender@localhost"
    msg["To"] = "lab-recipient@localhost"
    msg.set_content(
        "<h1>HTML mail</h1><p>View <strong>HTML</strong> tab in MailCatcher.</p>",
        subtype="html",
    )
    _send(msg, settings)
    return marker


def _scenario_multipart_alternative(settings: SmtpLabSettings) -> str:
    marker = "[smtp-lab:multipart-alt]"
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"{marker} text + html alternatives"
    msg["From"] = "lab-sender@localhost"
    msg["To"] = "lab-recipient@localhost"
    msg.attach(MIMEText("Plain fallback for old clients.", "plain", "utf-8"))
    msg.attach(MIMEText("<p>Rich <em>HTML</em> for modern clients.</p>", "html", "utf-8"))
    _send(msg, settings)
    return marker


def _scenario_cc_bcc(settings: SmtpLabSettings) -> str:
    marker = "[smtp-lab:cc-bcc]"
    msg = EmailMessage()
    msg["Subject"] = f"{marker} CC and BCC headers"
    msg["From"] = "lab-sender@localhost"
    msg["To"] = "primary@localhost"
    msg["Cc"] = "cc-peer@localhost"
    msg["Bcc"] = "hidden-bcc@localhost"
    msg.set_content("MailCatcher shows To/Cc; Bcc may still appear in dev capture tools.")
    _send(msg, settings)
    return marker


def _scenario_reply_to(settings: SmtpLabSettings) -> str:
    marker = "[smtp-lab:reply-to]"
    msg = EmailMessage()
    msg["Subject"] = f"{marker} Reply-To override"
    msg["From"] = "noreply@localhost"
    msg["To"] = "user@localhost"
    msg["Reply-To"] = "support@localhost"
    msg.set_content("From says noreply; Reply-To tells clients where answers should go.")
    _send(msg, settings)
    return marker


def _scenario_attachment(settings: SmtpLabSettings) -> str:
    marker = "[smtp-lab:attachment]"
    msg = MIMEMultipart("mixed")
    msg["Subject"] = f"{marker} file attachment"
    msg["From"] = "lab-sender@localhost"
    msg["To"] = "lab-recipient@localhost"
    msg.attach(MIMEText("See attached notes.txt in MailCatcher.", "plain", "utf-8"))
    part = MIMEApplication(b"SMTP lab attachment bytes\n", _subtype="octet-stream")
    part.add_header("Content-Disposition", "attachment", filename="notes.txt")
    msg.attach(part)
    _send(msg, settings)
    return marker


def _scenario_utf8(settings: SmtpLabSettings) -> str:
    marker = "[smtp-lab:utf8]"
    msg = EmailMessage()
    msg["Subject"] = f"{marker} Unicode — 日本語 — emoji"
    msg["From"] = "lab-sender@localhost"
    msg["To"] = "lab-recipient@localhost"
    msg.set_content("Body with emoji and accents: café, naïve, 邮件.")
    _send(msg, settings)
    return marker


def _scenario_multiple_to(settings: SmtpLabSettings) -> str:
    marker = "[smtp-lab:multi-to]"
    msg = EmailMessage()
    msg["Subject"] = f"{marker} multiple To addresses"
    msg["From"] = "lab-sender@localhost"
    msg["To"] = "alice@localhost, bob@localhost"
    msg.set_content("One message, several recipients in the To header.")
    _send(msg, settings)
    return marker


def _scenario_headers(settings: SmtpLabSettings) -> str:
    marker = "[smtp-lab:headers]"
    msg = EmailMessage()
    msg["Subject"] = f"{marker} custom X- headers"
    msg["From"] = "lab-sender@localhost"
    msg["To"] = "lab-recipient@localhost"
    msg["X-Smtp-Lab-Scenario"] = "headers"
    msg["X-Priority"] = "1"
    msg.set_content("Custom headers appear in MailCatcher source view.")
    _send(msg, settings)
    return marker


def _scenario_long_body(settings: SmtpLabSettings) -> str:
    marker = "[smtp-lab:long]"
    body = "Line of repeated content for wrapping tests.\n" * 80
    msg = EmailMessage()
    msg["Subject"] = f"{marker} long body"
    msg["From"] = "lab-sender@localhost"
    msg["To"] = "lab-recipient@localhost"
    msg.set_content(body)
    _send(msg, settings)
    return marker


SCENARIOS: dict[str, Scenario] = {
    s.id: s
    for s in [
        Scenario(
            "plain",
            "Plain text",
            "Single text/plain part via EmailMessage.",
            "[smtp-lab:plain]",
            _scenario_plain,
        ),
        Scenario(
            "html",
            "HTML only",
            "One part with subtype html.",
            "[smtp-lab:html]",
            _scenario_html,
        ),
        Scenario(
            "multipart-alt",
            "Multipart alternative",
            "text/plain + text/html; clients pick best display.",
            "[smtp-lab:multipart-alt]",
            _scenario_multipart_alternative,
        ),
        Scenario(
            "cc-bcc",
            "Cc / Bcc",
            "Multiple recipient headers.",
            "[smtp-lab:cc-bcc]",
            _scenario_cc_bcc,
        ),
        Scenario(
            "reply-to",
            "Reply-To",
            "Different reply address than From.",
            "[smtp-lab:reply-to]",
            _scenario_reply_to,
        ),
        Scenario(
            "attachment",
            "Attachment",
            "multipart/mixed with application/octet-stream.",
            "[smtp-lab:attachment]",
            _scenario_attachment,
        ),
        Scenario(
            "utf8",
            "UTF-8",
            "Non-ASCII subject and body.",
            "[smtp-lab:utf8]",
            _scenario_utf8,
        ),
        Scenario(
            "multi-to",
            "Multiple To",
            "Comma-separated To list.",
            "[smtp-lab:multi-to]",
            _scenario_multiple_to,
        ),
        Scenario(
            "headers",
            "Custom headers",
            "X-* and priority-style headers.",
            "[smtp-lab:headers]",
            _scenario_headers,
        ),
        Scenario(
            "long",
            "Long body",
            "Many lines to inspect wrapping.",
            "[smtp-lab:long]",
            _scenario_long_body,
        ),
    ]
}


def run_scenario(scenario_id: str, settings: SmtpLabSettings | None = None) -> str:
    cfg = settings or SmtpLabSettings.from_env()
    scenario = SCENARIOS.get(scenario_id)
    if scenario is None:
        known = ", ".join(sorted(SCENARIOS))
        raise KeyError(f"Unknown scenario {scenario_id!r}. Choose from: {known}")
    return scenario.run(cfg)


def run_all_scenarios(settings: SmtpLabSettings | None = None) -> list[tuple[str, str]]:
    cfg = settings or SmtpLabSettings.from_env()
    results: list[tuple[str, str]] = []
    for sid in SCENARIOS:
        marker = run_scenario(sid, cfg)
        results.append((sid, marker))
    return results
