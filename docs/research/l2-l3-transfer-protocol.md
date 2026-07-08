# L2 → L3 Transfer Protocol

**Status:** DRAFT
**Owner:** Research Agent

## Hypothesis

Episodic vectors in L2 (curated chunks) can be distilled into L3 **semantic concept nodes** via clustering, graph expansion, or LLM summarization; the best v1 path minimizes cost while preserving recall@10 for concept-level queries.

## Method

Formal comparison template per candidate:

```
H(c): hypothesis for candidate c
M(c): method steps
R(c): measurable results (recall, cost, complexity)
Rec(c): recommendation rank
```

### Candidates

| Rank | Algorithm class | H(c) | M(c) | Complexity | Prototype feasibility |
|------|-----------------|------|------|------------|------------------------|
| 1 | **HDBSCAN** on L2 embeddings | Density clusters = concepts without fixed K | Embed curated chunks → reduce optional → HDBSCAN → centroid label via top TF-IDF terms | O(n log n) typical; memory O(n) | **High** — sklearn/hdbscan on export batch |
| 2 | **k-means** (fixed K) | K concepts per domain module | Choose K from elbow/heuristic → k-means → label clusters | O(n·K·iter) | **High** — simplest baseline |
| 3 | **BFS on cosine graph** | Concepts = connected components above τ | Build k-NN graph in Qdrant or offline → BFS/union-find | O(n·k) edges | **Medium** — needs graph storage in payload |
| 4 | **LLM summarization pass** | Concepts = abstractive summaries per cluster | Cluster (1 or 2) → prompt LLM per cluster → store summary vector + text | API cost + latency | **Medium** — gated on local Ollama vs cloud |

### Evaluation dimensions (weights for research score)

| Dimension | Weight |
|-----------|--------|
| Retrieval utility (concept query recall@10) | 0.35 |
| Implementation effort | 0.25 |
| Runtime cost (CPU/$) | 0.20 |
| Explainability / audit | 0.10 |
| Incremental update (new notes) | 0.10 |

## Results

**Pilot expectation (micro-corpus, n < 20 chunks):** k-means and HDBSCAN collapse to trivial clusters; **not statistically decisive**. Protocol value is defining **production-scale** measurement:

1. Hold-out **concept queries** (human-written, 20+).
2. L3 nodes stored as Qdrant points with `payload.role=concept`, `payload.source_chunk_ids[]`.
3. Measure recall@10 linking concept → supporting chunks.

| Algorithm class | recall@10 (pilot) | Cost | Explainability | Incremental | **Weighted score** |
|-----------------|-------------------|------|----------------|-------------|---------------------|
| HDBSCAN | TBD | Low CPU | Medium | Re-cluster batch | TBD |
| k-means | TBD | Low CPU | Low | Re-run K | TBD |
| BFS graph | TBD | Medium | **High** (explicit edges) | Edge insert | TBD |
| LLM summarize | TBD | **High** | **High** | Re-prompt | TBD |

## Recommendation

**v1 prototype path:** **HDBSCAN (or k-means baseline)** on L2 embeddings → deterministic concept IDs → store in Qdrant with payload links. **Defer LLM summarization** to v2 for human-readable concept titles only, not primary structure.

**v1.5 enrichment:** Add **BFS/k-NN graph** edges between concepts for “related concept” navigation (aligns with Qdrant Agent graph-in-payload workstream).

**Human decision:** Orchestrator selects production algorithm class before L2/L3 Agent implements consolidation pass — see `AGENT_WORK_LOG.md` item 5.

## Open Questions

- Optimal **cluster granularity** per domain pack (WordNet vs finance modules).
- Whether L3 vectors are **centroids** or **separate embed(summary text)**.
- Consistency scoring / “dreaming” job interaction (Layer 3 roadmap).
