# Content sidecars (pre-multimodal ingestion)

OmniKB currently ingests `.md`, `.txt`, and `.pdf` as text. For other types, use a **Markdown sidecar** next to the asset so retrieval stays text-first and reviewable.

## Pattern

For an asset file `assets/diagram-network.png`:

- Keep the binary under `assets/` (or export-only; binaries can remain outside `data/sources` if you do not want them in the bind mount).
- Add `assets/diagram-network.md` (or `.md` beside the asset in `data/sources`) containing:
  - Title and short description
  - Labels, legend text, and entities shown in the diagram
  - Tags and links to related curated notes
  - Optional transcript or OCR text

Set `kb_source_type: media_sidecar` in frontmatter (see [obsidian-vault-conventions.md](obsidian-vault-conventions.md)).

## By type

| Type | Sidecar should include |
|------|-------------------------|
| **Images** | Visible text, UI strings, objects, scene description, OCR output if run externally. |
| **Diagrams (SVG/PNG)** | Node/edge semantics, acronyms, version, source tool export notes. |
| **Spreadsheets** | Sheet purpose, column definitions, key formulas in plain language, important cell ranges as text tables. |
| **Web captures** | Canonical URL, capture date, summary, quoted excerpts (respect copyright). |
| **Code snippets** | Path/repo, language, intent, inputs/outputs, security caveats (no live secrets). |

## Quality bar before widening ingest types

1. Sidecar is **human-reviewed** (`kb_status: approved`).
2. `python scripts/validate_corpus.py` passes with no errors for the exported tree.
3. `/ingest/preview` chunk boundaries look sensible for the sidecar.

Future multimodal embeddings can attach to the same logical document ID once the text sidecar pipeline is stable.
