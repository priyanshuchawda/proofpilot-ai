import os

import pytest

from app.ai.embeddings import EmbeddingRequest, GoogleGenAIEmbeddingProvider
from app.core.config import get_settings

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_GEMINI_EMBEDDING_SMOKE") != "1",
    reason="Real Gemini embedding smoke tests are opt-in only.",
)


async def test_real_gemini_embedding_smoke() -> None:
    settings = get_settings()
    provider = GoogleGenAIEmbeddingProvider(
        api_key=settings.gemini_api_key,
        output_dimension=settings.gemini_embedding_dimension,
    )

    response = await provider.embed_texts(
        EmbeddingRequest(
            texts=["ProofPilot validates citations against retrieved evidence."],
            model=settings.gemini_embedding_model,
            kind="document",
        )
    )

    assert response.model == settings.gemini_embedding_model
    assert response.dimension == settings.gemini_embedding_dimension
    assert len(response.vectors) == 1
    assert len(response.vectors[0]) == settings.gemini_embedding_dimension
