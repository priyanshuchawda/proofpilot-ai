from hashlib import sha256
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Document, DocumentChunk, DocumentVersion, IngestionJob
from app.ingestion.chunking import SourcePage, chunk_pages
from app.ingestion.extractors import extract_pages
from app.ingestion.redaction import redact_secrets
from app.ingestion.storage import LocalFileStorage
from app.ingestion.uploads import validate_upload_metadata


class DocumentService:
    def __init__(self, session: AsyncSession, storage_root: Path) -> None:
        self._session = session
        self._storage = LocalFileStorage(storage_root)

    async def ingest_upload(
        self,
        *,
        workspace_id: str,
        filename: str,
        content_type: str | None,
        content: bytes,
    ) -> Document:
        validate_upload_metadata(filename=filename, content_type=content_type, size=len(content))
        content_hash = sha256(content).hexdigest()
        storage_path = self._storage.save(
            filename=filename, content_hash=content_hash, content=content
        )

        document = Document(
            workspace_id=workspace_id,
            filename=filename,
            mime_type=content_type or "application/octet-stream",
            status="uploaded",
        )
        self._session.add(document)
        await self._session.flush()

        version = DocumentVersion(
            document_id=document.id,
            content_hash=content_hash,
            storage_path=str(storage_path),
            version_number=1,
        )
        self._session.add(version)
        await self._session.flush()

        document.current_version_id = version.id
        job = IngestionJob(document_version_id=version.id, status="uploaded")
        self._session.add(job)

        pages = extract_pages(filename, content)
        job.status = "parsed"

        redacted_pages: list[SourcePage] = []
        redaction_status = "clean"
        for page in pages:
            redacted = redact_secrets(page.text)
            if redacted.status == "redacted":
                redaction_status = "redacted"
            redacted_pages.append(SourcePage(page_number=page.page_number, text=redacted.text))

        chunks = chunk_pages(redacted_pages)
        job.status = "chunked"

        for chunk in chunks:
            self._session.add(
                DocumentChunk(
                    workspace_id=workspace_id,
                    document_id=document.id,
                    document_version_id=version.id,
                    source_filename=filename,
                    mime_type=document.mime_type,
                    page_number=chunk.page_number,
                    section_heading=chunk.section_heading,
                    chunk_order=chunk.chunk_order,
                    chunk_text=chunk.text,
                    token_estimate=chunk.token_estimate,
                    content_hash=sha256(chunk.text.encode("utf-8")).hexdigest(),
                    redaction_status=redaction_status,
                )
            )

        job.status = "ready"
        document.status = "ready"
        await self._session.commit()
        await self._session.refresh(document)
        return document

    async def list_documents(self, *, workspace_id: str) -> list[Document]:
        result = await self._session.execute(
            select(Document)
            .where(Document.workspace_id == workspace_id)
            .order_by(Document.created_at)
        )
        return list(result.scalars().all())

    async def get_document(self, *, document_id: str) -> Document | None:
        return await self._session.get(Document, document_id)

    async def chunk_count(self, *, document_id: str) -> int:
        result = await self._session.execute(
            select(func.count())
            .select_from(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
        )
        return int(result.scalar_one())
