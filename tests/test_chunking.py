from omnikb.domain.chunking import recursive_chunk_text


def test_recursive_chunking_respects_size() -> None:
    text = "Paragraph one.\n\nParagraph two with more words.\n\nParagraph three is here."
    chunks = recursive_chunk_text(text, chunk_size=30, chunk_overlap=0)
    assert chunks
    assert all(len(chunk) <= 30 for chunk in chunks)


def test_recursive_chunking_adds_overlap() -> None:
    text = "Alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu"
    chunks = recursive_chunk_text(text, chunk_size=24, chunk_overlap=6)
    assert len(chunks) > 1
    assert chunks[1].startswith(chunks[0][-6:].strip())
