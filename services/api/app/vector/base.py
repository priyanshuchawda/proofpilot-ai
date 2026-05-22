from collections.abc import Sequence
from typing import Protocol

from pydantic import BaseModel, Field


class VectorPoint(BaseModel):
    point_id: str
    chunk_id: str
    vector: list[float] = Field(min_length=1)


class VectorStore(Protocol):
    async def ensure_collection(self, *, dimension: int) -> None: ...

    async def upsert(self, points: Sequence[VectorPoint]) -> None: ...

    async def search(self, *, vector: list[float], limit: int) -> list[str]: ...
