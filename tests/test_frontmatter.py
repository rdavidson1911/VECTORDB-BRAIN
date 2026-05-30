from __future__ import annotations

from pathlib import Path

from omnikb.curation.frontmatter import as_bool, frontmatter_body, parse_frontmatter


def test_parse_frontmatter_coerces_unquoted_booleans(tmp_path: Path) -> None:
    path = tmp_path / "n.md"
    path.write_text("---\nkb_ingest: true\nflag: false\n---\n\nbody\n", encoding="utf-8")
    fm = parse_frontmatter(path)
    assert fm is not None
    assert fm["kb_ingest"] is True
    assert fm["flag"] is False


def test_parse_frontmatter_coerces_quoted_booleans(tmp_path: Path) -> None:
    path = tmp_path / "n.md"
    path.write_text('---\nkb_ingest: "true"\n---\n\nbody\n', encoding="utf-8")
    fm = parse_frontmatter(path)
    assert fm is not None
    assert as_bool(fm.get("kb_ingest")) is True


def test_parse_frontmatter_yes_no_synonyms(tmp_path: Path) -> None:
    path = tmp_path / "n.md"
    path.write_text("---\nai_assisted: yes\nverified: no\n---\n\nbody\n", encoding="utf-8")
    fm = parse_frontmatter(path)
    assert fm is not None
    assert as_bool(fm.get("ai_assisted")) is True
    assert as_bool(fm.get("verified")) is False


def test_parse_frontmatter_missing_fence_returns_none(tmp_path: Path) -> None:
    path = tmp_path / "n.md"
    path.write_text("# No frontmatter\n", encoding="utf-8")
    assert parse_frontmatter(path) is None


def test_parse_frontmatter_bom_and_crlf(tmp_path: Path) -> None:
    path = tmp_path / "n.md"
    path.write_bytes(b"\xef\xbb\xbf---\r\nkb_ingest: true\r\n---\r\n\r\nbody\r\n")
    fm = parse_frontmatter(path)
    assert fm is not None
    assert fm.get("kb_ingest") is True


def test_frontmatter_body_strips_fence(tmp_path: Path) -> None:
    path = tmp_path / "n.md"
    path.write_text("---\ntitle: x\n---\n\nHello body\n", encoding="utf-8")
    body = frontmatter_body(path)
    assert "Hello body" in body
    assert "---" not in body.split("Hello")[0] or body.strip().startswith("Hello")


def test_frontmatter_body_without_fence_returns_full_text(tmp_path: Path) -> None:
    path = tmp_path / "n.md"
    path.write_text("plain text only", encoding="utf-8")
    assert frontmatter_body(path) == "plain text only"
