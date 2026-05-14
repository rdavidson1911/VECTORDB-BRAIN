# Security Hardening Guide

This guide defines practical security hardening controls for VectorDB-Brain operations and development.

Use with:

- `docs/data-curation-pipeline.md`
- `docs/testing-framework.md`
- `README.md` quality commands

## 1) Security Posture

VectorDB-Brain is local-first but still requires strong controls for:

- sensitive corpus content,
- unsafe path access,
- dependency vulnerabilities,
- accidental data mutation,
- operational misconfiguration.

## 2) Data and Path Controls

### Raw corpus safety

- Treat `data/sources` as controlled source-of-truth input.
- In containerized runtime, maintain read-only mount semantics for raw corpus sources.
- Avoid writing derived artifacts back into raw corpus paths.

### Path validation policy

- Reject invalid/missing ingest paths with explicit error details.
- Prefer explicit allowlisted roots in operator procedures.
- Avoid broad system path targeting in automation scripts.

## 3) Secret and Sensitive Data Practices

- Do not commit secrets to repository files.
- Use environment variables for runtime configuration.
- Redact sensitive snippets before indexing where policy requires.
- Keep incident logs informative but free of secret material.

## 4) Security Quality Gates

Run these checks before merge:

```powershell
python -m bandit -c pyproject.toml -r src
python -m ruff check src tests
python -m mypy src
python -m pytest
```

Recommended periodic additions:

- dependency vulnerability scans,
- secret scanning policy in pre-commit/CI.

## 5) Runtime Context Checks

When troubleshooting service behavior:

1. Verify which process/container actually serves the endpoint.
2. Confirm expected port ownership and runtime mode.
3. Restart only the runtime context that owns the active path.
4. Re-test health and ingest paths after restart.

This prevents debugging against stale settings in the wrong runtime scope.

## 6) Incident and Evidence Handling

- Record smoke/test/security incidents in `devtools/error-tracking-db.md`.
- Include timestamp, failing check, observed behavior, and proposed remediation.
- Link security-impacting incidents to PR notes and follow-up tasks.

## 7) Planned Hardening Extensions (Not Implemented Yet)

- policy-driven path allowlist enforcement in API layer,
- stricter role separation for maintenance operations,
- enhanced provenance and signed artifact workflows for derived layers.
