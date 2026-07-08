"""Pytest fixtures for Research Agent benchmarks (Qdrant port 6334 only)."""

from __future__ import annotations

import os
from urllib.parse import urlparse

import pytest

RESEARCH_QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6334")
RESEARCH_COLLECTION = "research_lab"


def _research_port_ok(url: str) -> bool:
    parsed = urlparse(url)
    port = parsed.port
    if port is None:
        return parsed.hostname in ("localhost", "127.0.0.1")
    return port == 6334


@pytest.fixture(scope="session")
def qdrant_url() -> str:
    if not _research_port_ok(RESEARCH_QDRANT_URL):
        pytest.skip(f"QDRANT_URL must use port 6334 for research; got {RESEARCH_QDRANT_URL}")
    return RESEARCH_QDRANT_URL


@pytest.fixture(scope="session")
def research_collection() -> str:
    return RESEARCH_COLLECTION
