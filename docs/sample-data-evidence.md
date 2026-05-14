# Sample Data Evidence for Idempotent Rebuilds

This document records the exact sample corpus and API operations used to validate local vector ingestion and retrieval.

## Sample Corpus

- `data/sources/sample-note.md`
- `data/sources/sample-ops.txt`
- `data/sources/sample-rag.md`

## File Integrity (SHA256)

- `sample-note.md`: `A62F083DE0E1EDAA8C33887C4C5BC17BCA698485A68C3D15230B6D1684AD2FE4`
- `sample-ops.txt`: `721B64C31834C0D9B71949A70018B44E3C6366AFA61382C8B313706E6FBE2B84`
- `sample-rag.md`: `390F79B112842F10EB4AB9EDD56AD4031EA4541317D16803F5566C5462403179`

## Validation Commands

```powershell
Invoke-RestMethod -Method Get -Uri http://localhost:8000/health
Invoke-RestMethod -Method Post -Uri http://localhost:8000/ingest/path -ContentType application/json -Body '{"path":"/data/sources","recursive":true}'
Invoke-RestMethod -Method Post -Uri http://localhost:8000/query -ContentType application/json -Body '{"query":"Which ports are used by API and Qdrant?","limit":5}'
Invoke-RestMethod -Method Post -Uri http://localhost:8000/query -ContentType application/json -Body '{"query":"How does OmniKB retrieval augmented generation work?","limit":5}'
```

## Expected Signals

- `/health` returns `service: ok` and `qdrant: ok`
- `/ingest/path` returns `files_seen: 3`, `files_indexed: 3`, `chunks_indexed: 3`
- `/query` returns matches whose payload `source_path` values include:
  - `/data/sources/sample-note.md`
  - `/data/sources/sample-ops.txt`
  - `/data/sources/sample-rag.md`
