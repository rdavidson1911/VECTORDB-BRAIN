# Obsidian vault conventions (OmniKB-aligned)

Use Obsidian as the **authoring and review** layer; OmniKB remains the **search/index** layer over staged files under `data/sources` (see [obsidian-export-to-omnikb.md](obsidian-export-to-omnikb.md)).

## Folder layout (recommended)

| Area | Purpose |
|------|---------|
| `00-inbox/` | Raw captures, unreviewed imports. |
| `10-staging/` | Cleaned notes pending approval for indexing. |
| `20-curated/` | Approved knowledge ready to export to OmniKB. |
| `90-archive/` | Retired or superseded notes (usually not exported). |
| `assets/` | Binary media; each asset has a Markdown sidecar (see [content-sidecars.md](content-sidecars.md)). |

## Frontmatter / properties

Use YAML frontmatter at the top of Markdown notes. These keys map cleanly to a future generated corpus manifest and to OmniKB metadata policy:

| Key | Type | Purpose |
|-----|------|---------|
| `kb_status` | string | `draft`, `review`, `approved`, `deprecated`. |
| `kb_ingest` | boolean | If `true`, include in the next export to `data/sources`. |
| `kb_source_type` | string | `note`, `runbook`, `reference`, `meeting`, etc. |
| `kb_owner` | string | Person or team accountable for accuracy. |
| `kb_tags` | list or string | Free-form tags (mirror into manifest later). |
| `kb_reviewed_at` | ISO date | Last human review timestamp. |
| `kb_canonical_id` | string | Optional stable ID for dedupe across renames (future automation). |

Example:

```yaml
---
kb_status: approved
kb_ingest: true
kb_source_type: runbook
kb_owner: ops-team
kb_tags: [network, firewall]
kb_reviewed_at: 2026-05-02
---
```

## Principles

- **Plain Markdown first** — conventions must work without community plugins.
- **Decouple vault path from container path** — export/sync into `data/sources` preserves reproducible paths inside Docker (`/data/sources/...`).
- **No secrets in vault notes** that will be indexed; redact before `kb_ingest: true`.

See also [data-curation-pipeline.md](data-curation-pipeline.md) and [corpus-manifest-contract.md](corpus-manifest-contract.md).
