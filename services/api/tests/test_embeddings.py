from types import SimpleNamespace

from app.ai.embeddings import (
    DeterministicEmbeddingProvider,
    EmbeddingRequest,
    GoogleGenAIEmbeddingProvider,
    build_embedding_provider,
)
from app.core.config import Settings


async def test_deterministic_embedding_provider_returns_stable_vectors() -> None:
    provider = DeterministicEmbeddingProvider(dimension=16)

    first = await provider.embed_texts(
        EmbeddingRequest(texts=["ProofPilot evidence retrieval"], model="deterministic-local")
    )
    second = await provider.embed_texts(
        EmbeddingRequest(texts=["ProofPilot evidence retrieval"], model="deterministic-local")
    )

    assert first.model == "deterministic-local"
    assert first.dimension == 16
    assert first.vectors == second.vectors
    assert len(first.vectors[0]) == 16


class FakeEmbeddingModels:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def embed_content(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        return SimpleNamespace(embeddings=[SimpleNamespace(values=[0.1, 0.2, 0.3])])


class FakeEmbeddingClient:
    def __init__(self) -> None:
        self.aio = SimpleNamespace(models=FakeEmbeddingModels())


def fake_embedding_client_factory(api_key: str) -> FakeEmbeddingClient:
    assert api_key == "dev-key"
    return FakeEmbeddingClient()


async def test_google_embedding_provider_embeds_each_text_with_document_instruction() -> None:
    fake_client = fake_embedding_client_factory("dev-key")

    def client_factory(api_key: str) -> FakeEmbeddingClient:
        assert api_key == "dev-key"
        return fake_client

    provider = GoogleGenAIEmbeddingProvider(
        api_key="dev-key",
        output_dimension=3,
        client_factory=client_factory,
    )

    response = await provider.embed_texts(
        EmbeddingRequest(
            texts=["ProofPilot evidence.", "Citation integrity."],
            model="gemini-embedding-2",
            kind="document",
        )
    )

    calls = fake_client.aio.models.calls
    assert response.model == "gemini-embedding-2"
    assert response.dimension == 3
    assert response.vectors == [[0.1, 0.2, 0.3], [0.1, 0.2, 0.3]]
    assert len(calls) == 2
    assert calls[0]["model"] == "gemini-embedding-2"
    assert calls[0]["contents"].startswith("Represent this document for retrieval:")
    assert calls[0]["config"]["output_dimensionality"] == 3


def test_embedding_provider_factory_uses_real_provider_only_when_enabled_with_key() -> None:
    local_provider = build_embedding_provider(
        Settings(gemini_api_key="dev-key", gemini_embeddings_enabled=False)
    )
    real_provider = build_embedding_provider(
        Settings(gemini_api_key="dev-key", gemini_embeddings_enabled=True)
    )

    assert isinstance(local_provider, DeterministicEmbeddingProvider)
    assert isinstance(real_provider, GoogleGenAIEmbeddingProvider)
