from collections.abc import Sequence

import httpx

from app.vector.base import VectorPoint


class QdrantVectorStore:
    def __init__(self, *, url: str, collection: str) -> None:
        self._url = url.rstrip("/")
        self._collection = collection

    async def ensure_collection(self, *, dimension: int) -> None:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.put(
                f"{self._url}/collections/{self._collection}",
                json={"vectors": {"size": dimension, "distance": "Cosine"}},
            )
        response.raise_for_status()

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
