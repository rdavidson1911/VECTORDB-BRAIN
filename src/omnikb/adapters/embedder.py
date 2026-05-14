from __future__ import annotations

from functools import cached_property


class SentenceTransformerEmbedder:
    def __init__(self, model_name: str) -> None:
        self.model_name = model_name

    @cached_property
    def model(self):
        from sentence_transformers import SentenceTransformer

        return SentenceTransformer(self.model_name)

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        vectors = self.model.encode(texts, normalize_embeddings=True)
        return vectors.tolist()

    @property
    def dimensions(self) -> int:
        dim = self.model.get_sentence_embedding_dimension()
        if dim is None:
            raise RuntimeError("SentenceTransformer did not report embedding dimensions.")
        return int(dim)
