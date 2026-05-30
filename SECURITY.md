# Security

## Reporting a vulnerability

Please **do not** open a public GitHub issue for undisclosed security problems.

1. Open a **private** security advisory on GitHub (repository **Security** tab → **Report a vulnerability**), or
2. Contact the maintainers with a clear description, affected versions, and reproduction steps if possible.

We aim to acknowledge reports within a few business days. Critical fixes will be prioritized.

## Scope notes

- This project is intended for **local / self-hosted** use (Docker, local corpus). Threat models differ from multi-tenant SaaS; still report serious issues (remote code execution, unsafe defaults, auth bypasses if auth is added later, secret leakage).

## Good practices for operators

See [docs/security-hardening-guide.md](docs/security-hardening-guide.md) for hardening checklists and operational guidance.
