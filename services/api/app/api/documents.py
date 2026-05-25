from collections.abc import AsyncIterator
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.models import Document, Workspace
from app.db.session import get_db_session
from app.ingestion.queue import IngestionQueue, IngestionQueueUnavailableError, RedisIngestionQueue
from app.ingestion.uploads import UnsupportedUploadError, UploadTooLargeError
from app.security.local_session import (
    LocalSession,
    ensure_workspace_owner,
    get_local_session,
    ownership_enabled,
)
from app.security.rate_limiting import enforce_sensitive_rate_limit
from app.services.documents import DocumentService

router = APIRouter(tags=["documents"])


class DocumentResponse(BaseModel):
    id: str
    workspace_id: str
    filename: str
    mime_type: str
    status: str
    chunk_count: int


class DocumentStatusResponse(BaseModel):
    id: str
    status: str


def get_document_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DocumentService:
    return DocumentService(session, Path(".data/uploads"))


async def get_ingestion_queue(
    settings: Annotated[Settings, Depends(get_settings)],
) -> AsyncIterator[IngestionQueue]:
    queue = RedisIngestionQueue(url=settings.redis_url)
    try:
        yield queue
    finally:
        await queue.close()


async def to_document_response(
    document: Document,
    service: DocumentService,
) -> DocumentResponse:
    return DocumentResponse(
        id=document.id,
        workspace_id=document.workspace_id,
        filename=document.filename,
        mime_type=document.mime_type,
        status=document.status,
        chunk_count=await service.chunk_count(document_id=document.id),
    )


@router.post(
    "/api/v1/workspaces/{workspace_id}/documents",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    workspace_id: str,
    _rate_limit: Annotated[None, Depends(enforce_sensitive_rate_limit)],
    db_session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    local_session: Annotated[LocalSession, Depends(get_local_session)],
    service: Annotated[DocumentService, Depends(get_document_service)],
    queue: Annotated[IngestionQueue, Depends(get_ingestion_queue)],
    file: Annotated[UploadFile, File(...)],
) -> DocumentResponse:
    del _rate_limit
    await ensure_workspace_owner(
        workspace_id=workspace_id,
        session=db_session,
        local_session=local_session,
        settings=settings,
    )
    content = await file.read()
    try:
        document = await service.create_upload(
            workspace_id=workspace_id,
            filename=file.filename or "document",
            content_type=file.content_type,
            content=content,
        )
    except UploadTooLargeError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=str(exc)
        ) from exc
    except UnsupportedUploadError as exc:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=str(exc)
        ) from exc
    try:
        await queue.enqueue(document_id=document.id)
    except IngestionQueueUnavailableError as exc:
        await service.mark_failed(document_id=document.id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Document processing queue is unavailable. Try again later.",
        ) from exc

    return await to_document_response(document, service)


@router.get("/api/v1/workspaces/{workspace_id}/documents", response_model=list[DocumentResponse])
async def list_documents(
    workspace_id: str,
    db_session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    local_session: Annotated[LocalSession, Depends(get_local_session)],
    service: Annotated[DocumentService, Depends(get_document_service)],
) -> list[DocumentResponse]:
    await ensure_workspace_owner(
        workspace_id=workspace_id,
        session=db_session,
        local_session=local_session,
        settings=settings,
    )
    documents = await service.list_documents(workspace_id=workspace_id)
    return [await to_document_response(document, service) for document in documents]


@router.get("/api/v1/documents/{document_id}/status", response_model=DocumentStatusResponse)
async def document_status(
    document_id: str,
    db_session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    local_session: Annotated[LocalSession, Depends(get_local_session)],
    service: Annotated[DocumentService, Depends(get_document_service)],
) -> DocumentStatusResponse:
    document = await service.get_document(document_id=document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    if ownership_enabled(settings):
        workspace = await db_session.scalar(
            select(Workspace).where(Workspace.id == document.workspace_id)
        )
        if workspace is None or workspace.owner_session_id != local_session.session_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    return DocumentStatusResponse(id=document.id, status=document.status)
