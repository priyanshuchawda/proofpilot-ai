from collections.abc import Callable
from math import sqrt
from typing import Any, Literal, Protocol

from pydantic import BaseModel, Field

from app.ai.gemini import MissingGeminiApiKeyError
from app.core.config import Settings


class EmbeddingRequest(BaseModel):
    texts: list[str] = Field(min_length=1)
    model: str
    kind: Literal["document", "query"] = "document"


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


class GoogleGenAIEmbeddingProvider:
    def __init__(
        self,
        *,
        api_key: str | None,
        output_dimension: int,
        client_factory: Callable[[str], Any] | None = None,
    ) -> None:
        if not api_key:
            raise MissingGeminiApiKeyError("GEMINI_API_KEY is required for real Gemini embeddings.")
        self._api_key = api_key
        self._output_dimension = output_dimension
        self._client_factory = client_factory

    async def embed_texts(self, request: EmbeddingRequest) -> EmbeddingResponse:
        client = self._build_client()
        vectors: list[list[float]] = []
        for text in request.texts:
            response: Any = await client.aio.models.embed_content(
                model=request.model,
                contents=_embedding_instruction(text=text, kind=request.kind),
                config={"output_dimensionality": self._output_dimension},
            )
            vectors.append([float(value) for value in response.embeddings[0].values])
        return EmbeddingResponse(
            vectors=vectors,
            model=request.model,
            dimension=len(vectors[0]),
        )

    def _build_client(self) -> Any:
        if self._client_factory is not None:
            return self._client_factory(self._api_key)
        from google import genai

        return genai.Client(api_key=self._api_key)


def build_embedding_provider(settings: Settings) -> EmbeddingProvider:
    if not settings.gemini_embeddings_enabled:
        return DeterministicEmbeddingProvider()
    if not settings.gemini_api_key and settings.proofpilot_env == "development":
        return DeterministicEmbeddingProvider()
    return GoogleGenAIEmbeddingProvider(
        api_key=settings.gemini_api_key,
        output_dimension=settings.gemini_embedding_dimension,
    )


def _embedding_instruction(*, text: str, kind: str) -> str:
    if kind == "query":
        return f"Represent this search query for retrieving relevant documents: {text}"
    return f"Represent this document for retrieval: {text}"
