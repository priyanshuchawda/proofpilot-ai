from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Workspace
from app.db.session import get_db_session
from app.repositories.workspaces import WorkspaceRepository
from app.services.workspaces import WorkspaceService

router = APIRouter(prefix="/api/v1/workspaces", tags=["workspaces"])


class WorkspaceCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=2000)


class WorkspaceResponse(BaseModel):
    id: str
    name: str
    description: str | None


def to_workspace_response(workspace: Workspace) -> WorkspaceResponse:
    return WorkspaceResponse(
        id=workspace.id,
        name=workspace.name,
        description=workspace.description,
    )


def get_workspace_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> WorkspaceService:
    return WorkspaceService(WorkspaceRepository(session))


@router.post("", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    request: WorkspaceCreateRequest,
    service: Annotated[WorkspaceService, Depends(get_workspace_service)],
) -> WorkspaceResponse:
    workspace = await service.create_workspace(
        name=request.name,
        description=request.description,
    )
    return to_workspace_response(workspace)


@router.get("", response_model=list[WorkspaceResponse])
async def list_workspaces(
    service: Annotated[WorkspaceService, Depends(get_workspace_service)],
) -> list[WorkspaceResponse]:
    return [to_workspace_response(workspace) for workspace in await service.list_workspaces()]
