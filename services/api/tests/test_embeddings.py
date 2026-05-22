from app.ai.embeddings import DeterministicEmbeddingProvider, EmbeddingRequest


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
