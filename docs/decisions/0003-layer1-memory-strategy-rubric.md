# ADR 0003: Layer 1 Memory Strategy Rubric

**Status:** Accepted
**Date:** 2026-08-10
**Related:** [ADR 0002: Interaction Boost and Idle Dreaming](0002-interaction-boost-and-dreaming.md)

## Decision

Ingest assigns a `memory_tier` payload field on every Layer 1 chunk. Boost and dreaming workers consult this tier:

| memory_tier | Source pattern | Boost eligibility | Dreaming eligibility |
|---|---|---|---|
| `curated_note` | `curated/**/*.md` (Template 2.0.0) | full | full |
| `reference_pdf` | `*.pdf` (esp. under curated) | impression-only until click | low priority (edges only after click boost) |
| `samples` | `_samples/**` or `sample-*` | never | never |
| `staging` | `staging/**` | N/A (not routine-indexed) | N/A |
| `default` | other indexed text | full impressions + clicks | full |

Optional operator narrative: `docs/research/layer1-memory-strategy-rubric.md` (when present).

## Consequences

- Frontmatter gate and three-zone layout remain the integrity path for curated markdown.
- Rubric is enforced in code (`omnikb.domain.memory_tier`) rather than documentation alone.
