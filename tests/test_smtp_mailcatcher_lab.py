"""SMTP lab: unit checks + optional MailCatcher integration (learning / dev)."""

from __future__ import annotations

import pytest
from devtools.smtp_lab.api import MailcatcherApi
from devtools.smtp_lab.config import SmtpLabSettings
from devtools.smtp_lab.scenarios import SCENARIOS, run_scenario
from devtools.smtp_lab.smtp_check import smtp_reachable


def test_settings_defaults() -> None:
    cfg = SmtpLabSettings()
    assert cfg.smtp_host == "127.0.0.1"
    assert cfg.smtp_port == 1025
    assert "1081" in cfg.web_base_url


def test_all_scenarios_registered() -> None:
    assert len(SCENARIOS) >= 10
    for sid, scenario in SCENARIOS.items():
        assert scenario.id == sid
        assert scenario.subject_marker.startswith("[smtp-lab")


@pytest.fixture
def smtp_settings() -> SmtpLabSettings:
    return SmtpLabSettings.from_env()


@pytest.fixture
def mailcatcher_api(smtp_settings: SmtpLabSettings) -> MailcatcherApi:
    return MailcatcherApi(smtp_settings)


def _require_mailcatcher(smtp_settings: SmtpLabSettings) -> None:
    if not smtp_reachable(smtp_settings):
        host = smtp_settings.smtp_host
        port = smtp_settings.smtp_port
        pytest.skip(
            f"MailCatcher SMTP not reachable at {host}:{port}. "
            "Run: .\\scripts\\Start-MailCatcher.ps1"
        )
    api = MailcatcherApi(smtp_settings)
    try:
        api.list_messages()
    except OSError:
        pytest.skip(f"MailCatcher web UI not reachable at {smtp_settings.web_base_url}")


@pytest.mark.mailcatcher
@pytest.mark.parametrize("scenario_id", sorted(SCENARIOS.keys()))
def test_send_scenario_appears_in_mailcatcher(
    scenario_id: str,
    smtp_settings: SmtpLabSettings,
    mailcatcher_api: MailcatcherApi,
) -> None:
    _require_mailcatcher(smtp_settings)
    mailcatcher_api.clear_all()
    marker = run_scenario(scenario_id, smtp_settings)
    matches = mailcatcher_api.find_by_subject_contains(marker)
    assert len(matches) >= 1, f"Expected subject containing {marker!r} for scenario {scenario_id}"


@pytest.mark.mailcatcher
def test_send_all_scenarios_increases_mailbox(
    smtp_settings: SmtpLabSettings,
    mailcatcher_api: MailcatcherApi,
) -> None:
    _require_mailcatcher(smtp_settings)
    mailcatcher_api.clear_all()
    for sid in SCENARIOS:
        run_scenario(sid, smtp_settings)
    messages = mailcatcher_api.list_messages()
    assert len(messages) == len(SCENARIOS)
