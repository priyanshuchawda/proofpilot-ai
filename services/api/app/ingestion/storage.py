from pathlib import Path

from app.ingestion.uploads import safe_storage_name


class LocalFileStorage:
    def __init__(self, root: Path) -> None:
        self._root = root

    def save(self, *, filename: str, content_hash: str, content: bytes) -> Path:
        self._root.mkdir(parents=True, exist_ok=True)
        target = (self._root / safe_storage_name(filename, content_hash=content_hash)).resolve()
        root = self._root.resolve()
        if root not in target.parents:
            raise ValueError("Resolved upload path escaped storage root.")
        target.write_bytes(content)
        return target
