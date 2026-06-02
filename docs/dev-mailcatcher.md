# Local SMTP with MailCatcher (development only)

MailCatcher accepts mail over SMTP and shows messages in a browser UI. It is **not** a secure production mail server: there is **no authentication**, **no TLS**, and **no delivery** to the internet.

Use it only on **127.0.0.1** for local testing (OmniKB does not send mail today; this is for future features, scripts, or app experiments).

## Why `gem install mailcatcher` failed

MailCatcher is distributed as a Ruby gem. On your machine, Ruby is not installed, so PowerShell cannot find `gem`.

You do **not** need Ruby if you use Docker (recommended on this repo).

## Recommended: Docker (localhost-bound)

From the repo root:

```powershell
.\scripts\Start-MailCatcher.ps1
```

Or:

```powershell
docker compose --profile dev-mail up -d mailcatcher
```

| Service | Address |
|--------|---------|
| SMTP | `127.0.0.1:1025` (override: `MAILCATCHER_SMTP_PORT`) |
| Web UI | http://127.0.0.1:1081 (override: `MAILCATCHER_WEB_PORT`; default **1081** avoids clash with other stacks on **1080**) |

Stop:

```powershell
docker compose --profile dev-mail stop mailcatcher
```

### Port conflict on your machine

Another container (`penpot-mailcatch`) already uses host port **1080** (and is bound to `0.0.0.0`, which is wider exposure than localhost-only). OmniKB defaults the web UI to **1081** so both can run. SMTP **1025** is published for `omnikb-mailcatcher` only.

To reuse a single MailCatcher for everything, publish SMTP on the Penpot stack (`1025:1025`) and use http://127.0.0.1:1080 — or stop the other container when you only need OmniKB’s instance.

The compose service uses `profiles: [dev-mail]` so MailCatcher does **not** start with a normal `docker compose up`.

### App running in Docker vs on the host

| Client runs on | SMTP host | Port |
|----------------|-----------|------|
| Windows / PowerShell / Python on host | `127.0.0.1` | `1025` |
| `omnikb-api` container (with profile up) | `mailcatcher` | `1025` |

Optional `.env` entries (see `.env.example`): `SMTP_HOST`, `SMTP_PORT`.

## Security practices (local dev)

1. **Bind to localhost** — Compose maps `127.0.0.1:1025` and `127.0.0.1:1080` only, not `0.0.0.0`, so other machines on your LAN cannot connect.
2. **Dev profile only** — Do not enable `dev-mail` in production or shared servers.
3. **No secrets in test mail** — Treat captured messages as plain text on disk/in memory; do not send real passwords or API keys through MailCatcher.
4. **Do not relay** — MailCatcher never forwards to real providers; if you add app code, point **only** at MailCatcher in `APP_ENV=dev`.
5. **Firewall** — With localhost binding, Windows Firewall usually blocks remote access; avoid publishing these ports in cloud/VPN port forwards.

MailCatcher is **intentionally insecure** for convenience. “Secure local SMTP” here means **isolated to your machine**, not encrypted/authenticated SMTP.

## Smoke test (PowerShell)

With MailCatcher running:

```powershell
python -c @"
import smtplib
from email.message import EmailMessage
m = EmailMessage()
m['Subject'] = 'OmniKB MailCatcher test'
m['From'] = 'dev@localhost'
m['To'] = 'you@localhost'
m.set_content('If you see this in the web UI, SMTP works.')
with smtplib.SMTP('127.0.0.1', 1025, timeout=10) as s:
    s.send_message(m)
print('Sent — open http://127.0.0.1:1081')
"@
```

## Alternative: native Ruby on Windows

If you prefer `mailcatcher` without Docker:

1. Install [Ruby+Devkit](https://rubyinstaller.org/) (3.2.x or 3.3.x).
2. Open **“Start command prompt with Ruby”** and run:

   ```bat
   gem install mailcatcher
   ```

3. Start bound to localhost:

   ```bat
   mailcatcher --ip 127.0.0.1
   ```

Same ports by default: SMTP `1025`, web `1080`.

## Alternative: MailHog

Similar dev sink; Docker:

```powershell
docker run --rm -p 127.0.0.1:1025:1025 -p 127.0.0.1:8025:8025 mailhog/mailhog
```

Web UI: http://127.0.0.1:8025

---

## SMTP lab (mock sends + tests)

Hands-on kit under `devtools/smtp_lab/`: sends **10 message variations** (plain, HTML, multipart, Cc/Bcc, Reply-To, attachment, UTF-8, etc.) and reads the mailbox via MailCatcher’s HTTP API.

### 1. Start MailCatcher

```powershell
.\scripts\Start-MailCatcher.ps1
```

### 2. Explore scenarios

```powershell
python -m devtools.smtp_lab.cli demo
```

### 3. Send mock mail

```powershell
# One variation
python -m devtools.smtp_lab.cli send --scenario plain
python -m devtools.smtp_lab.cli send --scenario multipart-alt

# All variations (great for learning in the web UI)
python -m devtools.smtp_lab.cli send --all

# PowerShell wrapper
.\scripts\Invoke-SmtpLab.ps1 send -Scenario html
.\scripts\Invoke-SmtpLab.ps1 send -All
```

### 4. Inspect without the browser

```powershell
python -m devtools.smtp_lab.cli list
python -m devtools.smtp_lab.cli clear
```

Open **http://127.0.0.1:1081** to compare what you see in the UI vs CLI.

### 5. Automated integration tests

Runs only when MailCatcher is up; otherwise tests are **skipped** (CI stays green).

```powershell
# All tests (mailcatcher tests skip if SMTP is down)
python -m pytest tests/test_smtp_mailcatcher_lab.py -q

# Only MailCatcher integration (after Start-MailCatcher.ps1)
python -m pytest tests/test_smtp_mailcatcher_lab.py -m mailcatcher -q
```

### Scenario reference

| Id | What you practice |
|----|-------------------|
| `plain` | `EmailMessage` + `text/plain` |
| `html` | HTML subtype |
| `multipart-alt` | `multipart/alternative` (plain + HTML) |
| `cc-bcc` | `Cc` / `Bcc` headers |
| `reply-to` | `Reply-To` vs `From` |
| `attachment` | `multipart/mixed` + file part |
| `utf8` | Unicode subject/body |
| `multi-to` | Multiple `To` addresses |
| `headers` | Custom `X-*` headers |
| `long` | Large body / wrapping |

Override host/ports with `SMTP_HOST`, `SMTP_PORT`, `MAILCATCHER_WEB` (see `.env.example`).
