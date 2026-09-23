"""Unit tests for memory_tier helpers."""

from omnikb.domain.memory_tier import dreaming_allowed, event_weight


def test_event_weights() -> None:
    assert event_weight("query_impression") == 1.0
    assert event_weight("result_click") == 3.0
    assert event_weight("unknown") == 0.0


def test_dreaming_allowed() -> None:
    assert dreaming_allowed("samples", has_click_boost=True) is False
    assert dreaming_allowed("reference_pdf", has_click_boost=False) is False
    assert dreaming_allowed("reference_pdf", has_click_boost=True) is True
    assert dreaming_allowed("curated_note", has_click_boost=False) is True
