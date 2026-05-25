import re
from dataclasses import dataclass
from typing import Annotated

from fastapi import Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.db.models import Workspace

LOCAL_ANONYMOUS_SESSION_ID = "local-anonymous"
SESSION_HEADER_NAME = "X-ProofPilot-Session"
_SESSION_ID_PATTERN = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")


@dataclass(frozen=True)
class LocalSession:
    session_id: str


def get_local_session(
    session_header: Annotated[str | None, Header(alias=SESSION_HEADER_NAME)] = None,
) -> LocalSession:
    session_id = session_header or LOCAL_ANONYMOUS_SESSION_ID
    if not _SESSION_ID_PATTERN.fullmatch(session_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid local session identifier.",
        )
    return LocalSession(session_id=session_id)


async def ensure_workspace_owner(
    *,
    workspace_id: str,
    session: AsyncSession,
    local_session: LocalSession,
    settings: Settings,
) -> Workspace | None:
    if not settings.proofpilot_workspace_ownership_enabled:
        return None
    workspace = await session.get(Workspace, workspace_id)
    if workspace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found.")
    if workspace.owner_session_id != local_session.session_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found.")
    return workspace


def ownership_enabled(settings: Settings) -> bool:
    return settings.proofpilot_workspace_ownership_enabled
