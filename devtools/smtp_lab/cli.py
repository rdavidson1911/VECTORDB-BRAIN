from __future__ import annotations

import argparse
import sys

from devtools.smtp_lab.api import MailcatcherApi
from devtools.smtp_lab.config import SmtpLabSettings
from devtools.smtp_lab.scenarios import SCENARIOS, run_all_scenarios, run_scenario
from devtools.smtp_lab.smtp_check import smtp_reachable


def _cmd_send(args: argparse.Namespace) -> int:
    settings = SmtpLabSettings.from_env()
    if not smtp_reachable(settings):
        print(
            f"SMTP not reachable at {settings.smtp_host}:{settings.smtp_port}. "
            "Start MailCatcher: .\\scripts\\Start-MailCatcher.ps1",
            file=sys.stderr,
        )
        return 2
    if args.all:
        for sid, marker in run_all_scenarios(settings):
            print(f"  sent {sid}: {marker}")
        print(f"\nOpen {settings.web_base_url} to inspect messages.")
        return 0
    marker = run_scenario(args.scenario, settings)
    print(f"Sent scenario {args.scenario!r} ({marker})")
    print(f"Web UI: {settings.web_base_url}")
    return 0


def _cmd_list(_: argparse.Namespace) -> int:
    api = MailcatcherApi()
    messages = api.list_messages()
    if not messages:
        print("Mailbox empty.")
        return 0
    for m in messages:
        mid = m.get("id", "?")
        subj = m.get("subject", "(no subject)")
        sender = m.get("sender", "?")
        print(f"  [{mid}] {subj}  from {sender}")
    print(f"\nTotal: {len(messages)} — UI: {api.web_base_url}")
    return 0


def _cmd_clear(_: argparse.Namespace) -> int:
    MailcatcherApi().clear_all()
    print("Cleared all messages in MailCatcher.")
    return 0


def _cmd_demo(_: argparse.Namespace) -> int:
    print("SMTP lab scenarios (dev only):\n")
    for s in SCENARIOS.values():
        print(f"  {s.id:16}  {s.title}")
        print(f"    {s.description}")
        print(f"    subject contains: {s.subject_marker}\n")
    print("Try:")
    print("  python -m devtools.smtp_lab.cli send --scenario plain")
    print("  python -m devtools.smtp_lab.cli send --all")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Send mock mail to local MailCatcher and inspect the mailbox (learning / dev)."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    send_p = sub.add_parser("send", help="Send one or all mock messages via SMTP")
    send_p.add_argument("--scenario", choices=sorted(SCENARIOS), help="Scenario id")
    send_p.add_argument("--all", action="store_true", help="Run every scenario")
    send_p.set_defaults(func=_cmd_send)

    list_p = sub.add_parser("list", help="List messages via MailCatcher HTTP API")
    list_p.set_defaults(func=_cmd_list)

    clear_p = sub.add_parser("clear", help="Delete all captured messages")
    clear_p.set_defaults(func=_cmd_clear)

    demo_p = sub.add_parser("demo", help="Print scenario catalog")
    demo_p.set_defaults(func=_cmd_demo)

    args = parser.parse_args(argv)
    if args.command == "send" and not args.all and not args.scenario:
        send_p.error("use --scenario <id> or --all")
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
