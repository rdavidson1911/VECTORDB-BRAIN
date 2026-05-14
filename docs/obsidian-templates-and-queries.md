# Obsidian templates and review queries

Templates and saved searches reduce curation errors before export to OmniKB. No custom plugin code is required; use core **Templates** and optional **Dataview** only if your vault already uses it.

## Core Templates plugin

Create notes under a `templates/` folder, then enable **Settings → Core plugins → Templates**.

### New curated note

File: `templates/kb-curated-note.md`

```markdown
---
kb_status: draft
kb_ingest: false
kb_source_type: note
kb_owner:
kb_tags: []
kb_reviewed_at:
---

# {{title}}

## Summary


## Details


## Links

```

Insert via command palette: **Templates: Insert template**.

### Media sidecar stub

File: `templates/kb-asset-sidecar.md`

```markdown
---
kb_status: draft
kb_ingest: false
kb_source_type: media_sidecar
kb_owner:
kb_tags: []
---

# Asset: {{image_name}}

## Description


## OCR / labels (if any)


## Related notes

```

## Dataview-style queries (optional)

If the **Dataview** community plugin is enabled, add a dashboard note `dashboards/kb-ingest-queue.md`:

````markdown
```dataview
TABLE kb_status, kb_reviewed_at, kb_owner
FROM "20-curated"
WHERE kb_ingest = true AND kb_status = "approved"
SORT kb_reviewed_at DESC
```
````

Notes:

- If Dataview is not installed, keep the same filters as a **manual search** in the file explorer (`kb_ingest: true` text search).
- OmniKB does not read Dataview blocks; they are for human workflow only.

## Saved searches (no plugins)

Use Obsidian **search** queries saved in a pinned note, for example:

- `path:20-curated kb_ingest:true kb_status:approved`
- `path:00-inbox kb_status:draft`

Pair with [validate_corpus.py](../scripts/validate_corpus.py) after each export for automated hygiene checks.
