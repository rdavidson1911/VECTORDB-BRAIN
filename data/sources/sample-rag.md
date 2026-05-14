# RAG Design Notes

Retrieval-augmented generation in OmniKB depends on:

1. chunking source documents
2. embedding chunks with sentence-transformers
3. storing vectors and metadata in Qdrant
4. querying similar vectors using cosine similarity
