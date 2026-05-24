from collections.abc import Sequence
from typing import Any

import httpx

from app.vector.base import VectorPoint


class QdrantCollectionConfigurationError(RuntimeError):
    """Raised when an existing collection cannot accept the configured vectors."""


class QdrantVectorStore:
    _distance = "Cosine"

    def __init__(self, *, url: str, collection: str) -> None:
        self._url = url.rstrip("/")
        self._collection = collection

    async def ensure_collection(self, *, dimension: int) -> None:
        async with httpx.AsyncClient(timeout=10) as client:
            existing = await client.get(f"{self._url}/collections/{self._collection}")
            if existing.status_code == 200:
                self._validate_collection_dimension(response=existing, dimension=dimension)
                return
            if existing.status_code != 404:
                existing.raise_for_status()
            response = await client.put(
                f"{self._url}/collections/{self._collection}",
                json={"vectors": {"size": dimension, "distance": self._distance}},
            )
            if response.status_code == 409:
                existing = await client.get(f"{self._url}/collections/{self._collection}")
                existing.raise_for_status()
                self._validate_collection_dimension(response=existing, dimension=dimension)
                return
        response.raise_for_status()

    def _validate_collection_dimension(self, *, response: httpx.Response, dimension: int) -> None:
        payload: Any = response.json()
        vector_configuration = payload["result"]["config"]["params"]["vectors"]
        existing_dimension: object = vector_configuration["size"]
        existing_distance: object = vector_configuration["distance"]
        if existing_dimension != dimension:
            raise QdrantCollectionConfigurationError(
                f"Qdrant collection {self._collection!r} uses vector dimension "
                f"{existing_dimension!r}; configured dimension is {dimension}."
            )
        if existing_distance != self._distance:
            raise QdrantCollectionConfigurationError(
                f"Qdrant collection {self._collection!r} uses vector distance "
                f"{existing_distance!r}; configured distance is {self._distance!r}."
            )

    async def upsert(self, points: Sequence[VectorPoint]) -> None:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.put(
                f"{self._url}/collections/{self._collection}/points",
                params={"wait": "true"},
                json={
                    "points": [
                        {
                            "id": point.point_id,
                            "vector": point.vector,
                            "payload": {"chunk_id": point.chunk_id},
                        }
                        for point in points
                    ]
                },
            )
        response.raise_for_status()

    async def search(self, *, vector: list[float], limit: int) -> list[str]:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                f"{self._url}/collections/{self._collection}/points/search",
                json={"vector": vector, "limit": limit, "with_payload": True},
            )
        response.raise_for_status()
        result = response.json()["result"]
        return [point["payload"]["chunk_id"] for point in result]
