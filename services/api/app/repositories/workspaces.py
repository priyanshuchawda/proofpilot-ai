from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Workspace


class WorkspaceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, *, name: str, description: str | None) -> Workspace:
        workspace = Workspace(name=name, description=description)
        self._session.add(workspace)
        await self._session.commit()
        await self._session.refresh(workspace)
        return workspace

    async def list(self) -> list[Workspace]:
        result = await self._session.execute(select(Workspace).order_by(Workspace.created_at))
        return list(result.scalars().all())
