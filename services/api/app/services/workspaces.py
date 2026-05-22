from app.db.models import Workspace
from app.repositories.workspaces import WorkspaceRepository


class WorkspaceService:
    def __init__(self, repository: WorkspaceRepository) -> None:
        self._repository = repository

    async def create_workspace(self, *, name: str, description: str | None) -> Workspace:
        return await self._repository.create(name=name.strip(), description=description)

    async def list_workspaces(self) -> list[Workspace]:
        return await self._repository.list()
