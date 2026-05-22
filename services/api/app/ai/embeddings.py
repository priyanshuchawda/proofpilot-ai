from math import sqrt
from typing import Protocol

from pydantic import BaseModel, Field


class EmbeddingRequest(BaseModel):
    texts: list[str] = Field(min_length=1)
    model: str


class EmbeddingResponse(BaseModel):
    vectors: list[list[float]]
    model: str
    dimension: int


class EmbeddingProvider(Protocol):
    async def embed_texts(self, request: EmbeddingRequest) -> EmbeddingResponse: ...


class DeterministicEmbeddingProvider:
    def __init__(self, *, dimension: int = 64) -> None:
        self._dimension = dimension

    async def embed_texts(self, request: EmbeddingRequest) -> EmbeddingResponse:
        return EmbeddingResponse(
            vectors=[self._embed(text) for text in request.texts],
            model=request.model,
            dimension=self._dimension,
        )

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self._dimension
        tokens = [token.lower() for token in text.split() if token.strip()]
        for token in tokens:
            index = sum(ord(char) for char in token) % self._dimension
            vector[index] += 1.0

        magnitude = sqrt(sum(value * value for value in vector))
        if magnitude == 0:
            return vector
        return [value / magnitude for value in vector]
