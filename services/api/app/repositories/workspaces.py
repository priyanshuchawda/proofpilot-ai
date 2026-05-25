from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Workspace


class WorkspaceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        name: str,
        description: str | None,
        owner_session_id: str,
    ) -> Workspace:
        workspace = Workspace(
            name=name,
            description=description,
            owner_session_id=owner_session_id,
        )
        self._session.add(workspace)
        await self._session.commit()
        await self._session.refresh(workspace)
        return workspace

    async def list(self, *, owner_session_id: str | None = None) -> list[Workspace]:
        statement = select(Workspace).order_by(Workspace.created_at)
        if owner_session_id is not None:
            statement = statement.where(Workspace.owner_session_id == owner_session_id)
        result = await self._session.execute(statement)
        return list(result.scalars().all())
