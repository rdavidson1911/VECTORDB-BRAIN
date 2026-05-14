from __future__ import annotations

import argparse
import json
from pathlib import Path

from omnikb.curation.manifest import build_manifest_document

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a JSON corpus manifest for supported files."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=ROOT / "data" / "sources",
        help="Directory (or file) to scan (default: data/sources).",
    )
    parser.add_argument(
        "--relative-to",
        type=Path,
        default=ROOT,
        help="Paths in manifest are relative to this directory (default: repo root).",
    )
    parser.add_argument(
        "--recursive",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Recurse into subdirectories (default: true).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "data" / "processed" / "curation" / "corpus-manifest-latest.json",
        help="Output JSON path.",
    )
    parser.add_argument(
        "--dated-copy",
        action="store_true",
        help="Write an additional timestamped copy next to the main output.",
    )
    args = parser.parse_args()

    doc = build_manifest_document(
        args.root.resolve(),
        relative_to=args.relative_to.resolve(),
        recursive=args.recursive,
    )
    text = json.dumps(doc, indent=2)
    out = args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(f"Wrote manifest to {out}")

    if args.dated_copy:
        stamp = doc["generated_at"].replace(":", "").replace("-", "")
        dated = out.with_name(f"corpus-manifest-{stamp}.json")
        dated.write_text(text, encoding="utf-8")
        print(f"Wrote dated copy to {dated}")


if __name__ == "__main__":
    main()
