# Meeting Prep: Episodic Learning & Reactive Architecture in VECTORDB-BRAIN

**Date:** Monday, June 1, 2026
**Topic:** How episodic memory research informs VECTORDB-BRAIN's layered architecture

---

## 1. Executive Summary

VECTORDB-BRAIN (OmniKB) is evolving beyond naive RAG toward a **layered knowledge architecture** that mirrors how human episodic memory works. The system uses **reactive programming patterns** (React state, event handlers, async flows) to create a responsive interface that makes memory formation and retrieval feel natural and immediate.

---

## 2. The Problem with Naive RAG ("Fifty First Dates")

Traditional RAG systems:
- Start fresh every session with no memory of past interactions
- Only retrieve raw text chunks without context of how conclusions were reached
- Cannot distinguish between stable knowledge and temporary working hypotheses
- Lack provenance - no audit trail of why something was retrieved

**Human analogy:** Like having amnesia and rebuilding understanding from scratch every conversation.

---

## 3. The Layered Knowledge Architecture

VECTORDB-BRAIN introduces three layers that parallel human memory systems:

| Layer | System Purpose | Human Memory Analogy |
|-------|---------------|---------------------|
| **Layer 1** | Immutable raw corpus (`.md`, `.txt`, `.pdf`) | Long-term declarative memory (facts) |
| **Layer 2** | Session artifacts, interpretations, working notes | Working memory / episodic buffer |
| **Layer 3** | Persistent relationship graph with consistency scores | Semantic memory consolidation |

### Layer 1: Raw Source Layer (Implemented)
- Read-only canonical documents
- Full provenance tracking (`source_path`, `chunk_index`, `content_hash`)
- Evidence locker - never mutated by sessions

### Layer 2: Session and Cache Layer (Planned)
- Temporary artifacts created during user sessions
- Derived notes, summaries, intermediate relationships
- Promotion path: session artifacts can become durable derived documents
- Working group whiteboard - collaborative but ephemeral

### Layer 3: Relationship and Consistency Layer (Planned)
- Graph-like edges between chunks/documents
- Consistency/inconsistency scores from dreaming process
- Aggregation layer for query-time insight
- Curated institutional memory with audit trails

---

## 4. The "Dreaming" Process

Inspired by how human memory consolidates during sleep, the planned **dreaming process** runs after session completion:

**Inputs:**
- Layer 1 raw chunks
- Layer 2 session artifacts
- Existing relationship history

**Tasks:**
1. Compare chunk-level semantic and metadata consistency
2. Create/update edges between related nodes
3. Assign consistency metrics (strongly consistent, mixed, inconsistent)
4. Persist scores and provenance to Layer 3

**Outputs:**
- Edge records with score/version metadata
- Aggregated relationship summaries
- Trace links back to Layer 1 and Layer 2 sources

---

## 5. Reactive Programming in the Frontend

The React/Vite frontend uses reactive patterns that mirror neurological event processing:

### Event-Driven State Updates
```typescript
// State changes propagate through the system reactively
const [matches, setMatches] = useState<QueryMatch[]>([])
const [analytics, setAnalytics] = useState<SearchAnalytics | null>(null)
```

### Correlation-Based Logging
```typescript
// Every interaction creates a traceable correlation ID
uiLogInteraction('click', 'Search button', { handler: 'runSearch' }, correlationId)
```

### Parallel Data Loading
```typescript
// Dashboard loads health, summary, and sources concurrently
const [healthResp, summaryResp, sourceResp] = await Promise.all([
  api.getHealth(ctx),
  api.getCorpusSummary(ctx),
  api.getCorpusSources(ctx),
])
```

### UI Branding Reflects Architecture
- "L0 Corpus" - Layer 0/1 raw document status
- "Reactive Query" - Event-driven query analytics
- "Layer 0 Ingest" - Document ingestion into base layer

---

## 6. Neurological Dysfunction Analogies

VECTORDB-BRAIN's architecture can help explain neurological conditions:

| Condition | System Analogy | What It Teaches |
|-----------|---------------|-----------------|
| **OCD** | Excessive dreaming/consistency checking - Layer 3 runs too often, over-scores inconsistencies | Why some brains get stuck in verification loops |
| **ADHD** | Layer 2 session artifacts don't promote well - working memory clears too fast | Why information doesn't "stick" to long-term storage |
| **Amnesia** | Layer 1 intact but Layer 2/3 broken - raw facts exist but can't form new episodes | Why someone can know facts but not remember learning them |
| **Confabulation** | Layer 3 creates edges without proper Layer 1 evidence | Why some memories feel real but aren't grounded in actual events |

---

## 7. Why This Matters

1. **Explainability**: Every retrieved result traces back to source evidence
2. **Evolvability**: Session insights become durable knowledge over time
3. **Multi-client support**: Same API serves React, Streamlit, mobile, desktop
4. **Domain flexibility**: Architecture supports science, finance, psychology, etc.
5. **Educational value**: Demonstrates memory concepts in working software

---

## 8. Current Implementation Status

| Component | Status |
|-----------|--------|
| Layer 1 (ingest, chunk, embed, store, query) | **IMPLEMENTED** |
| React console with reactive state | **IMPLEMENTED** |
| Correlation-based UI logging | **IMPLEMENTED** |
| Data quality gates and validation | **IMPLEMENTED** |
| Layer 2 session artifacts | PLANNED |
| Dreaming process | PLANNED |
| Layer 3 relationship graph | PLANNED |
| Layer-aware query API | PLANNED |
| Drill-down UI | PLANNED |

---

## 9. Discussion Topics for Monday

### A. PDF Elimination Cost-Benefit Analysis

Should we remove `.pdf` support from the Qdrant vector store? This requires a full SDLC cost-benefit analysis:

| Dimension | Questions to Answer |
|-----------|-------------------|
| **Statistical** | What % of our corpus is PDF? What's the chunk quality difference vs. markdown? |
| **Financial** | PDF parsing libraries (licensing, maintenance), storage delta, compute cost for OCR |
| **Computational** | PDF extraction CPU/memory overhead vs. native text formats |
| **Storage** | Raw PDF size vs. extracted text, embedding storage per format |
| **Retrieval performance** | Query latency, relevance scores by source format |
| **Ingestion performance** | Time-to-index for PDF vs. md/txt |
| **Provenance impact** | Can we still prove where knowledge came from without original PDFs? Is this economically feasible now or in the future? |

**Key risk:** Eliminating PDFs might make provenance tracking infeasible - we could lose the ability to trace back to authoritative source documents (academic papers, legal docs, official reports).

### B. Technology Variation Fatigue & Pattern Recognition (NEW ROADMAP ITEM)

During tonight's discussion, we identified a critical missing piece in our roadmap: **pattern recognition across technology variations**.

The problem: Every new framework, language, or tool feels like starting from scratch. But underneath the syntax differences, the same fundamental patterns repeat:
- State management (Redux, Zustand, MobX, Signals, Atoms)
- Dependency injection (Spring, Angular, NestJS, Python's dependency-injector)
- Reactive streams (RxJS, RxPy, Project Reactor, Combine)
- ORM patterns (ActiveRecord, Repository, Unit of Work)

**Proposed addition to roadmap:**

> **Layer 4 (Conceptual): Cross-Domain Pattern Recognition**
> - Extract invariant patterns from technology-specific implementations
> - Build "rosetta stone" mappings between equivalent concepts
> - Enable queries like "show me the state management pattern" that return examples across React, Vue, Angular, Svelte
> - Reduce cognitive load of learning by surfacing what's the SAME, not just what's different

This is **constitutional-level thinking** for learn2earndao - defining the fundamental structures before adding amendments. The current roadmap focuses on storage/retrieval mechanics (Layers 1-3), but this proposes a higher-order abstraction layer for **knowledge transfer across domains**.

### C. Original Discussion Topics

1. **Priority of Layer 2 vs Layer 3** - Should we build session artifacts or relationships first?
2. **Dreaming trigger points** - When exactly should background reconciliation run?
3. **Consistency scoring algorithms** - What makes two chunks "consistent"?
4. **UI drill-down UX** - How should users navigate between layers?
5. **Domain-specific extensions** - What fields matter for different knowledge domains?

---

## 10. Key Files to Review

- `docs/layered-knowledge-architecture.md` - Architecture vision
- `docs/implementation-roadmap-layered-architecture.md` - Phased delivery plan
- `docs/vision-beyond-rag.md` - Why this matters
- `web/src/App.tsx` - Reactive frontend patterns
- `src/omnikb/api/schemas.py` - API contracts (includes planned fields)

---

*Prepared for Monday meeting discussion. Rest well!*
