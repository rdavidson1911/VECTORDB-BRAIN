# Pro-forma: ColBERT multivectors in episodic multi-layer memory

**Status:** Hypothetical / architecture exploration — **not implemented** in the current stack (dense MiniLM + single vector per chunk in Qdrant).

Related:

- [layered-knowledge-architecture.md](layered-knowledge-architecture.md)
- [architecture-graphviz.md](architecture-graphviz.md) — current + planned layers
- DOT source: [architecture-colbert-multivector-proforma.dot](architecture-colbert-multivector-proforma.dot)

---

## Why ColBERT multivectors here?

| Approach | What is stored per chunk | Retrieval |
|----------|-------------------------|-----------|
| **Current (dense)** | One embedding per chunk | Cosine similarity vs one query vector |
| **ColBERT multivector** | Many vectors per chunk (e.g. per token) | **Late interaction**: MaxSim between query token vectors and document token vectors |

ColBERT-style retrieval often improves **lexical grounding** and **phrase-level** match quality versus a single pooled embedding, at the cost of **larger indexes** and a dedicated scoring step. In VECTORDB-BRAIN terms, it is a **pluggable retrieval strategy** under the reactive query layer, not a replacement for Layer 0/1 provenance or Layer 3 relationship memory.

---

## How layers map (pro-forma)

| Layer | Role with ColBERT |
|--------|-------------------|
| **Layer 0 / 1** | Ingest still produces canonical chunks + hashes. **Additional** write path: ColBERT encoder emits **token multivectors** per chunk into a ColBERT-capable index (alongside or instead of dense-only). |
| **Layer 2 (episodic)** | Each query session records: query text, chosen strategy (`colbert` / `dense` / `hybrid`), top-k hit IDs, MaxSim scores. Optional **session cache** of query multivectors for reruns. This is the **episodic** trace that feeds consolidation. |
| **Reactive processing** | **Policy diamond**: route to ColBERT MaxSim path, dense Qdrant path, or fuse both. Outputs ranked chunks with provenance for UI and for Layer 2 logging. |
| **Layer 3** | **Dreaming** may use ColBERT **chunk↔chunk** MaxSim to propose relationship edges and consistency signals (complementing LLM reconciliation). Aggregates and audit trail record `score_model` / index version. |

---

## Logical processing flow (narrative)

1. **Ingest (offline)**
   Raw files → chunks → **dual index orchestrator** → dense index (today) + ColBERT multivector index (pro-forma).

2. **Query (online)**
   User question → reactive orchestrator → if ColBERT: encode query multivectors → **MaxSim** over token vectors in candidate chunks → optional fusion with dense top-k → return hits with `source_path`, scores, layer flags.

3. **Episodic capture (online, async-friendly)**
   Hit set and query representation appended to **Layer 2 session log** (and optional cache).

4. **Consolidation (offline)**
   On session end → dreaming job reads L1 chunks, L2 traces, ColBERT index samples → proposes Layer 3 edges → audit trail.

5. **Drill-down (planned)**
   Layer 3 aggregate → expand to Layer 1 chunk evidence (and L2 session note if any), same as existing roadmap; ColBERT only changes **how** candidates are ranked, not provenance rules.

---

## Render the diagram

From repo root (Graphviz installed):

```bash
dot -Tsvg docs/architecture-colbert-multivector-proforma.dot -o docs/architecture-colbert-multivector-proforma.svg
dot -Tpng docs/architecture-colbert-multivector-proforma.dot -o docs/architecture-colbert-multivector-proforma.png
```

Or paste the contents of `architecture-colbert-multivector-proforma.dot` into [Graphviz Online](https://dreampuf.github.io/GraphvizOnline/).

---

## Implementation notes (when you adopt this)

- **Storage:** Qdrant multivector collections, a dedicated ColBERT index service, or hybrid (dense prefetch → ColBERT rerank).
- **API:** Extend `QueryRequest` with e.g. `retrieval_strategy: "dense" | "colbert" | "hybrid"` and document score fields in responses.
- **Episodic store:** SQLite/Postgres or object store for session traces; keep separate from immutable `data/sources`.
- **Versioning:** Record `colbert_model`, `index_build_id`, and `maxsim_variant` in payload and audit trail for reproducibility.

---

## Comparison to current runtime

Today:

```text
sources → chunk → single embed → Qdrant → cosine search → UI
```

Pro-forma with ColBERT:

```text
sources → chunk → ┬→ dense embed → Qdrant
                  └→ ColBERT token vectors → multivector index
query → policy → MaxSim (and/or dense) → fuse → UI + Layer 2 episodic log → (dream) → Layer 3
```

This preserves **read-only Layer 0/1** while making **search** and **episodic memory** richer; Layer 3 remains the place for **durable** relational structure beyond a single retrieval call.
