from app.db.models import Workspace
from app.repositories.workspaces import WorkspaceRepository


class WorkspaceService:
    def __init__(self, repository: WorkspaceRepository) -> None:
        self._repository = repository

    async def create_workspace(
        self,
        *,
        name: str,
        description: str | None,
        owner_session_id: str,
    ) -> Workspace:
        return await self._repository.create(
            name=name.strip(),
            description=description,
            owner_session_id=owner_session_id,
        )

    async def list_workspaces(self, *, owner_session_id: str | None = None) -> list[Workspace]:
        return await self._repository.list(owner_session_id=owner_session_id)
