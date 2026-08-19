import os
from pathlib import Path
from typing import Protocol


class DocumentStorage(Protocol):
    """Abstract private document storage interface."""

    def store(self, key: str, data: bytes) -> str:
        """Stores document bytes under an opaque storage key and returns storage URI."""
        ...

    def retrieve(self, key: str) -> bytes:
        """Retrieves raw document bytes by opaque storage key."""
        ...

    def exists(self, key: str) -> bool:
        """Checks if key exists in storage."""
        ...

    def delete(self, key: str) -> bool:
        """Deletes document from storage."""
        ...


class LocalDocumentStorage:
    """
    Local filesystem secure document storage implementation.
    Stores documents in a private directory segregated from static/public assets.
    """

    def __init__(self, base_dir: str | Path | None = None):
        if base_dir is None:
            # Default private storage location under backend/storage/payslips
            base_dir = Path(__file__).resolve().parent.parent.parent / "storage" / "payslips"
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _get_path(self, key: str) -> Path:
        # Prevent directory traversal
        sanitized_key = os.path.basename(key)
        return self.base_dir / sanitized_key

    def store(self, key: str, data: bytes) -> str:
        target_path = self._get_path(key)
        target_path.write_bytes(data)
        return str(target_path)

    def retrieve(self, key: str) -> bytes:
        target_path = self._get_path(key)
        if not target_path.exists():
            raise FileNotFoundError(f"Document with key '{key}' not found in storage.")
        return target_path.read_bytes()

    def exists(self, key: str) -> bool:
        return self._get_path(key).exists()

    def delete(self, key: str) -> bool:
        target_path = self._get_path(key)
        if target_path.exists():
            target_path.unlink()
            return True
        return False
