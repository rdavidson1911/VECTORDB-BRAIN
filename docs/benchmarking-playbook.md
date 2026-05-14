# Chunking and Retrieval Benchmarking Playbook

This playbook standardizes how we measure chunking quality/speed and keep tuning decisions reproducible.

Chunk defaults should align with broader curation and governance goals (provenance, dedupe, when to re-embed): see [data-curation-pipeline.md](data-curation-pipeline.md).

## 1) Run chunking benchmark

From repo root:

```powershell
python scripts/benchmark_chunking.py
```

Options (see `python scripts/benchmark_chunking.py --help`):

- `--source-dir` — alternate corpus directory (default: `data/sources`)
- `--limit-files` — cap file count for quick runs
- `--output-name` / `--out-dir` — control JSON location
- `--dated-copy` — also write a timestamped JSON next to the latest file

Output file:

- `data/processed/benchmarks/chunking-benchmark-latest.json`

## 2) Compare strategy outcomes

Review the `summary` section in the JSON for:

- `avg_chunks_per_file`
- `avg_elapsed_ms_per_file`
- `avg_chunk_chars`

Primary candidate strategies:

- `recursive_char_v1`
- `markdown_structure_v1`
- `token_recursive_v1`

## 3) Validate retrieval behavior

After choosing a chunking default, rebuild and run API smoke:

```powershell
docker compose up --build -d api
.\scripts\smoke-test.ps1
```

Confirm:

- query returns relevant sources
- latency remains acceptable
- no regressions in endpoint responses

## 4) Capture evidence for retrospectives

For each benchmark cycle:

1. Save benchmark JSON in `data/processed/benchmarks/` (date-stamped copy optional).
2. Add summary notes and tradeoff decision to `devtools/error-tracking-db.md` or project docs.
3. Include selected defaults and rationale in PR description.

## 5) Current recommended local default

- Strategy: `markdown_structure_v1`
- Chunk size: `500`
- Chunk overlap: `60`

Reasoning: keeps chunks contextual for markdown-heavy notes while preserving fast split time and stable retrieval behavior.
