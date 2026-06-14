# Research benchmarks

Runs **only** against Qdrant on port **6334** (`research_lab` collection prefix).

## Prerequisites

```powershell
docker start qdrant-research
# Verify: http://localhost:6334/collections
```

## Run (recommended: API image)

Host Python on Windows may fail importing `sentence_transformers` (torchcodec). Use the project API image:

```powershell
docker run --rm -v "I:/VECTORDB-BRAIN:/app" -w /app `
  -e PYTHONPATH=/app/src `
  -e QDRANT_URL=http://host.docker.internal:6334 `
  vectordb-brain-api python docs/research/benchmarks/embedding_eval.py
```

Subset of models (faster):

```powershell
-e RESEARCH_BENCHMARK_MODELS=all-MiniLM-L6-v2,all-mpnet-base-v2
```

Output: `docs/research/artifacts/embedding_benchmark_latest.json`

## Pytest

```powershell
$env:QDRANT_URL = "http://localhost:6334"
python -m pytest docs/research/benchmarks/ -v --tb=short
```
