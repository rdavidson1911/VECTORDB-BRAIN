# Performance Profiling and Continuous Improvement

This guide standardizes how VectorDB-Brain measures performance, tracks regressions, and records continuous-improvement outcomes.

Primary references:

- `docs/benchmarking-playbook.md`
- `docs/data-curation-pipeline.md`
- `devtools/error-tracking-db.md`
- `docs/testing-framework.md`

## 1) Performance Objectives

Focus on measurable behavior in these paths:

- ingest throughput and stability,
- query latency and result quality,
- dashboard and smoke responsiveness,
- chunking strategy trade-offs.

## 2) Baseline Metrics

Track these metrics per run:

- ingest duration (end-to-end),
- files indexed, files skipped, chunks indexed,
- query latency (`analytics.latency_ms`),
- top score and average score trends,
- smoke pass/fail outcomes by check name.

Persist evidence in:

- benchmark JSON (`data/processed/benchmarks/`),
- incident log (`devtools/error-tracking-db.md`),
- PR descriptions for perf-affecting changes.

## 3) Profiling Workflow

### Step A: Baseline

1. Run quality gates (`ruff`, `mypy`, `bandit`, `pytest`).
2. Capture benchmark baseline:

```powershell
python scripts/benchmark_chunking.py
```

3. Run smoke:

```powershell
.\scripts\smoke-test.ps1
npm run smoke:playwright
```

### Step B: Compare

- Compare benchmark summary fields:
  - `avg_chunks_per_file`
  - `avg_elapsed_ms_per_file`
  - `avg_chunk_chars`
- Compare query analytics before/after change.
- Compare smoke stability and failure modes.

### Step C: Record

- Document outcomes and trade-offs.
- Mark whether changes are improvement, neutral, or regression.
- Store follow-up tasks for unresolved regressions.

## 4) Regression Response Policy

If regression is detected:

1. Confirm reproducibility.
2. Isolate layer (loader/chunker/embedder/store/query/UI).
3. Add or update a targeted test.
4. Record a mitigation plan and expected completion window.
5. Avoid shipping unbounded regressions without explicit waiver.

## 5) Continuous Improvement Loop

Use this repeating loop:

1. Observe: benchmark and smoke evidence.
2. Analyze: identify bottlenecks or instability.
3. Prioritize: choose highest impact/lowest risk improvements.
4. Implement: scoped change with tests.
5. Verify: rerun benchmark/smoke.
6. Capture: archive evidence and decision notes.

## 6) Planned Future Work (Not Yet Implemented)

- automated benchmark comparison reports in CI,
- trend dashboard for ingest/query metrics,
- expanded workload profiles (small/medium/large corpus sets),
- optional profiling of “dreaming” background process once implemented.
