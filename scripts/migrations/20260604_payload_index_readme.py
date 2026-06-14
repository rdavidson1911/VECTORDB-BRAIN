"""Payload index migration template (documentation only — idempotent checklist).

Purpose
-------
Describe how to add Qdrant payload indices for OmniKB Layer 1 (`omnikb_documents`)
without applying changes from this file. Executable migrations must be reviewed by
the Orchestrator and run explicitly against the **production** Qdrant URL supplied
via environment (see scripts/migrations/README.md).

Research / tuning
-----------------
HNSW and quantization experiments use port **6334** and collection `learning_lab` only.
Do not embed host port 6333 in new experiment scripts.

Idempotent pattern (pseudocode)
-------------------------------
1. Connect with QdrantClient(url=os.environ["QDRANT_URL"]).
2. For each (field_name, schema_type) in INDEX_SPEC:
   - Try create_payload_index(collection, field_name, field_schema=schema_type).
   - If index exists, log and continue.
3. Never delete collections or points.

Suggested INDEX_SPEC for omnikb_documents (priority order)
----------------------------------------------------------
- source_path          -> keyword
- indexed_at_ts        -> float
- file_type            -> keyword
- document_id          -> keyword
- content_hash         -> keyword
- chunk_strategy       -> keyword
- embedding_model      -> keyword
- pipeline_version     -> keyword
- normalization_profile -> keyword
- chunk_size           -> integer
- chunk_overlap        -> integer
- updated_at_ts        -> float  (future range filters)

L2 collection omnikb_episodes
-----------------------------
Defer until consolidation-trigger ADR and embedding-model decision; indices should
mirror episodic payload fields in docs/research/qdrant-schema-audit.md §4.2.

This module is intentionally comment-only. Implement create_payload_index calls in a
separate dated migration script after Orchestrator approval.
"""
