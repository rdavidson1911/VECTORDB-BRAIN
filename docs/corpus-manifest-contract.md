# Corpus manifest contract

The corpus manifest is a **JSON document** produced by `scripts/generate_corpus_manifest.py` (or any compatible tool). It records filesystem and content fingerprints for every supported file under a scan root so operators can diff manifests over time, verify integrity against [sample-data-evidence.md](sample-data-evidence.md), and feed future automation (staging, skip-if-unchanged, dedupe reports).

## Top-level fields

| Field | Type | Description |
|-------|------|-------------|
| `manifest_version` | string | Schema version; currently `1`. |
| `generated_at` | string | UTC RFC3339-like timestamp (`YYYY-MM-DDTHH:MM:SSZ`). |
| `root` | string | Absolute resolved scan root (POSIX slashes). |
| `entries` | array | Sorted list of per-file records. |

## Entry fields (`entries[]`)

| Field | Type | Description |
|-------|------|-------------|
| `source_path` | string | Path relative to the repository root (or chosen `--relative-to`), POSIX slashes. |
| `absolute_path` | string | Resolved absolute path for debugging. |
| `file_type` | string | Extension without dot (`md`, `txt`, `pdf`). |
| `size_bytes` | int | Filesystem size from `stat`. |
| `source_mtime_iso` | string | Source file mtime in UTC (same semantics as ingestion payload `updated_at`). |
| `content_hash` | string | SHA-256 hex (lowercase) of **extracted UTF-8 text** after loader rules (`errors="ignore"` for text; PDF via `pypdf`). |
| `char_count` | int | Length of extracted text string. |
| `ingest_eligible` | bool | `true` if stripped text is non-empty (OmniKB will index zero-chunk files as not indexed). |

## Hash comparison

`content_hash` is case-insensitive hex; [sample-data-evidence.md](sample-data-evidence.md) may list hashes in uppercase for readability.

## Output location

Default write path (gitignored except parent `.gitkeep`):

- `data/processed/curation/corpus-manifest-latest.json`

Use `--output` to override. Committed reference:

- [samples/corpus-manifest-sample.json](samples/corpus-manifest-sample.json)

## Obsidian mapping (future)

Optional frontmatter keys (`kb_status`, `kb_ingest`, etc.) described in [obsidian-vault-conventions.md](obsidian-vault-conventions.md) can later be merged into manifest entries by an export step; the v1 contract does not require them.
