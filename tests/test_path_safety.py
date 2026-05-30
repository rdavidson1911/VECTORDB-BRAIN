from pathlib import Path

import pytest

from omnikb.config.host_paths import canonical_data_sources_path, resolve_host_sources_root
from omnikb.domain.path_safety import (
    UnsafePathError,
    map_host_path_to_container,
    resolve_ingest_path,
    sanitize_path_input,
)


def test_sanitize_rejects_traversal_and_metacharacters() -> None:
    with pytest.raises(UnsafePathError):
        sanitize_path_input("../etc/passwd")
    with pytest.raises(UnsafePathError):
        sanitize_path_input("/data/sources/foo;rm -rf /")


def test_sanitize_accepts_windows_backslashes() -> None:
    assert (
        sanitize_path_input(r"I:\VECTORDB-BRAIN\data\sources\dax.pdf")
        == "I:/VECTORDB-BRAIN/data/sources/dax.pdf"
    )


def test_map_host_windows_path_without_host_root_uses_marker() -> None:
    mapped = map_host_path_to_container(
        "I:/VECTORDB-BRAIN/data/sources/dax.pdf",
        container_root="/data/sources",
        host_root=None,
    )
    assert mapped == "/data/sources/dax.pdf"


def test_map_host_windows_path_to_container() -> None:
    mapped = map_host_path_to_container(
        "I:/VECTORDB-BRAIN/data/sources/notes.md",
        container_root="/data/sources",
        host_root="I:/VECTORDB-BRAIN/data/sources",
    )
    assert mapped == "/data/sources/notes.md"


def test_resolve_data_sources_relative_prefix_no_double(tmp_path: Path) -> None:
    root = tmp_path / "data" / "sources"
    root.mkdir(parents=True)
    samples = root / "_samples"
    samples.mkdir()
    file_path = samples / "sample-note.md"
    file_path.write_text("hello", encoding="utf-8")

    resolved = resolve_ingest_path(
        "data/sources/_samples/sample-note.md",
        allowed_root=root,
        host_sources_root=None,
    )
    assert resolved == file_path.resolve()


def test_resolve_confines_under_root(tmp_path: Path) -> None:
    root = tmp_path / "sources"
    root.mkdir()
    file_path = root / "doc.md"
    file_path.write_text("hello", encoding="utf-8")

    resolved = resolve_ingest_path(
        "doc.md",
        allowed_root=root,
        host_sources_root=None,
    )
    assert resolved == file_path.resolve()


def test_canonical_data_sources_path_uses_docker_mount_when_present(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    orig_is_dir = Path.is_dir

    def patched_is_dir(self: Path) -> bool:
        if self.as_posix().replace("\\", "/").rstrip("/") == "/data/sources":
            return True
        return orig_is_dir(self)

    monkeypatch.setattr(Path, "is_dir", patched_is_dir)
    assert canonical_data_sources_path("./data/sources") == "/data/sources"


def test_canonical_data_sources_path_resolves_relative_on_host(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sources = tmp_path / "data" / "sources"
    sources.mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    assert canonical_data_sources_path("./data/sources") == str(sources.resolve())


def test_resolve_host_sources_skips_docker_in_container_path() -> None:
    assert resolve_host_sources_root("", "/data/sources") is None


def test_resolve_ingest_path_root_with_trailing_slash_does_not_double(tmp_path: Path) -> None:
    """Regression: sending the sources root itself (trailing slash) must
    resolve to root, not root/root."""
    root = tmp_path / "data" / "sources"
    root.mkdir(parents=True)

    resolved = resolve_ingest_path(
        root.as_posix() + "/",
        allowed_root=root,
        host_sources_root=None,
    )
    assert resolved == root.resolve()


def test_resolve_rejects_escape_outside_root(tmp_path: Path) -> None:
    root = tmp_path / "sources"
    root.mkdir()
    outside = tmp_path / "outside.md"
    outside.write_text("x", encoding="utf-8")

    with pytest.raises(UnsafePathError):
        resolve_ingest_path(
            str(outside),
            allowed_root=root,
            host_sources_root=None,
        )
