from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from omnikb.adapters.document_loader import discover_files, load_document
from omnikb.domain.chunking import ChunkingConfig, chunk_text

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_DIR = ROOT / "data" / "sources"
OUT_DIR = ROOT / "data" / "processed" / "benchmarks"

DEFAULT_CONFIGS: list[ChunkingConfig] = [
    ChunkingConfig(strategy="recursive_char_v1", chunk_size=350, chunk_overlap=35),
    ChunkingConfig(strategy="recursive_char_v1", chunk_size=500, chunk_overlap=60),
    ChunkingConfig(strategy="recursive_char_v1", chunk_size=650, chunk_overlap=80),
    ChunkingConfig(strategy="markdown_structure_v1", chunk_size=500, chunk_overlap=60),
    ChunkingConfig(strategy="token_recursive_v1", chunk_size=500, chunk_overlap=60),
]


@dataclass(slots=True)
class ChunkBenchmarkRow:
    source_path: str
    strategy: str
    chunk_size: int
    chunk_overlap: int
    chunk_count: int
    avg_chunk_chars: float
    elapsed_ms: float


def run_benchmark(
    source_dir: Path,
    *,
    limit_files: int | None = None,
    configs: list[ChunkingConfig] | None = None,
) -> dict:
    files = sorted(discover_files(str(source_dir), recursive=True))
    if limit_files is not None:
        files = files[:limit_files]
    if not files:
        raise SystemExit(f"No source files found in {source_dir}.")

    configs = configs or DEFAULT_CONFIGS
    rows: list[ChunkBenchmarkRow] = []
    for config in configs:
        for file_path in files:
            text = load_document(file_path).text
            started = time.perf_counter()
            chunks = chunk_text(text, config)
            elapsed_ms = (time.perf_counter() - started) * 1000.0
            avg_chars = (sum(len(c) for c in chunks) / len(chunks)) if chunks else 0.0
            rows.append(
                ChunkBenchmarkRow(
                    source_path=str(file_path.relative_to(ROOT)),
                    strategy=config.strategy,
                    chunk_size=config.chunk_size,
                    chunk_overlap=config.chunk_overlap,
                    chunk_count=len(chunks),
                    avg_chunk_chars=round(avg_chars, 3),
                    elapsed_ms=round(elapsed_ms, 3),
                )
            )

    summary: dict[str, dict[str, float]] = {}
    for row in rows:
        key = f"{row.strategy}:{row.chunk_size}:{row.chunk_overlap}"
        slot = summary.setdefault(
            key,
            {
                "runs": 0.0,
                "total_chunks": 0.0,
                "total_elapsed_ms": 0.0,
                "avg_chunk_chars_total": 0.0,
            },
        )
        slot["runs"] += 1
        slot["total_chunks"] += row.chunk_count
        slot["total_elapsed_ms"] += row.elapsed_ms
        slot["avg_chunk_chars_total"] += row.avg_chunk_chars

    summary_out = {}
    for key, slot in summary.items():
        runs = slot["runs"] or 1.0
        summary_out[key] = {
            "avg_chunks_per_file": round(slot["total_chunks"] / runs, 3),
            "avg_elapsed_ms_per_file": round(slot["total_elapsed_ms"] / runs, 3),
            "avg_chunk_chars": round(slot["avg_chunk_chars_total"] / runs, 3),
        }

    return {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source_dir": str(source_dir.resolve()).replace("\\", "/"),
        "files_benchmarked": len(files),
        "rows": [asdict(r) for r in rows],
        "summary": summary_out,
        "recommended_default": {
            "strategy": "markdown_structure_v1",
            "chunk_size": 500,
            "chunk_overlap": 60,
            "reason": (
                "Balanced chunk counts with fast local split time for markdown-heavy corpora."
            ),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Chunking benchmark harness for OmniKB.")
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=DEFAULT_SOURCE_DIR,
        help="Directory of source files to benchmark (default: data/sources).",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=OUT_DIR,
        help="Output directory for JSON (default: data/processed/benchmarks).",
    )
    parser.add_argument(
        "--output-name",
        type=str,
        default="chunking-benchmark-latest.json",
        help="Primary output filename (default: chunking-benchmark-latest.json).",
    )
    parser.add_argument(
        "--limit-files",
        type=int,
        default=None,
        help="Benchmark at most this many files (sorted by path).",
    )
    parser.add_argument(
        "--dated-copy",
        action="store_true",
        help="Also write chunking-benchmark-<generated_at stamp>.json beside the latest file.",
    )
    args = parser.parse_args()

    result = run_benchmark(args.source_dir.resolve(), limit_files=args.limit_files)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    text = json.dumps(result, indent=2)
    out_file = args.out_dir / args.output_name
    out_file.write_text(text, encoding="utf-8")
    print(f"Wrote benchmark output to {out_file}")

    if args.dated_copy:
        stamp = result["generated_at"].replace(":", "").replace("-", "")
        dated = args.out_dir / f"chunking-benchmark-{stamp}.json"
        dated.write_text(text, encoding="utf-8")
        print(f"Wrote dated copy to {dated}")


if __name__ == "__main__":
    main()
