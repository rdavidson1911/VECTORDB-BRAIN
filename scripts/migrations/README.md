# Qdrant Migration Scripts

This directory holds Python migration scripts produced by the **Qdrant Agent**.
Scripts here modify collection schemas, add payload indices, or apply quantization configs.

## Naming Convention
```
YYYYMMDD_<description>.py
```

## Rules
- Scripts are idempotent — safe to run twice without corrupting data.
- Scripts target the **production** Qdrant instance (port 6333) and must be reviewed by the Orchestrator before execution.
- Each script logs its actions before and after to stdout.
- Never DELETE a collection. Use collection aliases to swap schemas safely.

## Running a Migration
```bash
QDRANT_URL=http://localhost:6333 python scripts/migrations/YYYYMMDD_description.py
```
