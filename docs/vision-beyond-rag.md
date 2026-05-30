# Vision: layered memory vs naive RAG

Retrieval augmented generation (RAG) built only on chunked source text and vector similarity answers many questions, but it can behave like **“fifty first dates”**: each session starts from the same raw slices, with limited persistence of **negotiated understanding** that emerges when people and tools discuss the corpus together.

OmniKB / VECTORDB-BRAIN is evolving toward a **layered knowledge architecture** (see [layered-knowledge-architecture.md](layered-knowledge-architecture.md)):

| Layer | Role | Analogy |
|--------|------|--------|
| **Layer 1** | Immutable raw corpus and provenance | Evidence locker |
| **Layer 2** | Session artifacts, interpretations, intermediate links | Working group whiteboard |
| **Layer 3** | Durable relationship and consistency graph with scores and audit trails | Curated institutional memory |

Derived layers are **additive**: they do not replace Layer 1; they record *how* conclusions were reached and point back to source chunks for verification—similar in spirit to **hexagonal / ports-and-adapters** design: stable domain boundaries, swappable clients, and an honest history of inputs.

**Important:** Much of Layer 2 and Layer 3 is **roadmapped**, not fully built yet. The current stack (ingest, Qdrant, query API, React console) is the foundation; see [implementation-roadmap-layered-architecture.md](implementation-roadmap-layered-architecture.md) for phased delivery and tests.

Contributors who care about explainable, evolvable knowledge systems—and alternative UIs over the same API—are welcome. See [CONTRIBUTING.md](../CONTRIBUTING.md).
