# Obsidian export boundary for OmniKB

OmniKB ingests from `data/sources` inside the API container (`/data/sources`). Obsidian vaults usually live elsewhere. Treat the boundary explicitly so indexing stays reproducible and Git-friendly.

## Recommended default: staged copy

1. **Author** in Obsidian (`20-curated/`, approved notes with `kb_ingest: true`).
2. **Export or sync** approved Markdown (and sidecars) into the repo’s `data/sources/` tree on disk.
3. **Validate** before ingest:
   - `python scripts/validate_corpus.py --root data/sources`
4. **Optional manifest** for auditing:
   - `python scripts/generate_corpus_manifest.py`
5. **Ingest** via API or UI:
   - `POST /ingest/path` with `{"path":"/data/sources","recursive":true}`
   - Optional: `"skip_unchanged": true` after the first full index, to save embed cost when pipeline settings are unchanged.

## Why not bind-mount the vault directly?

- Vaults often contain plugins, large binaries, and notes not meant for retrieval.
- Staging enforces an explicit **approval gate** and keeps `.gitignore` rules predictable.
- Paths inside the container stay stable (`/data/sources/...`) regardless of host Obsidian location.

## Automation options (pick one later)

- **Manual copy** — `Copy-Item` / `robocopy` from vault `20-curated` to `data/sources` (simplest).
- **Git submodule or second clone** — advanced; only if you need version-linked vaults.
- **Small sync script** — a future repo script can filter by frontmatter `kb_ingest` (not required for v1).

## Path and case rules

- Container paths are **case-sensitive**; Windows hosts are not — avoid names that only differ by case.
- Prefer **POSIX-style slashes** in docs and manifests for readability.

See [obsidian-vault-conventions.md](obsidian-vault-conventions.md) and [data-curation-pipeline.md](data-curation-pipeline.md).
