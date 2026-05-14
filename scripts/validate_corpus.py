from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from omnikb.curation.validate import report_to_dict, validate_corpus

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Dry-run corpus validation (no ingest, no vector store writes)."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=ROOT / "data" / "sources",
        help="Directory to scan (default: data/sources).",
    )
    parser.add_argument(
        "--recursive",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Recurse into subdirectories (default: true).",
    )
    parser.add_argument(
        "--max-file-bytes",
        type=int,
        default=None,
        help="Warn when a file exceeds this size in bytes (default: 25 MiB).",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        default=None,
        help="If set, write full validation report JSON to this path.",
    )
    args = parser.parse_args()

    report = validate_corpus(
        args.root.resolve(),
        recursive=args.recursive,
        max_file_bytes=args.max_file_bytes,
    )
    payload = report_to_dict(report)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"Wrote report to {args.json_out}")

    errors = sum(1 for i in report.issues if i.severity == "error")
    warns = sum(1 for i in report.issues if i.severity == "warn")
    print(f"Scanned entries: {report.entries_scanned}")
    print(f"Issues: {len(report.issues)} (errors={errors}, warns={warns}, info=...)")
    if report.duplicate_content_hashes:
        print(f"Duplicate content_hash groups: {len(report.duplicate_content_hashes)}")
    for issue in report.issues:
        prefix = f"[{issue.severity}] {issue.code}"
        loc = f" {issue.path}" if issue.path else ""
        print(f"{prefix}{loc}: {issue.message}")

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
