"""
app/services/storage.py
───────────────────────
Document storage abstraction with a local filesystem implementation.

The abstraction allows swapping to S3 or Cloud Storage without changing
any business logic — the API routes import DocumentStorageService only.

Security requirements enforced here:
  - Files stored outside the public static directory.
  - Raw paths never returned; only document IDs.
  - MIME type validated against an allowlist.
  - File extensions cross-checked against MIME type.
  - Executable and dangerous extensions rejected.
  - Filenames sanitized before storage.
  - File size enforced before writing.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from app.schemas.profile import (
    ALLOWED_MIME_TYPES,
    MAX_FILE_SIZE_BYTES,
    DocumentMetadata,
)

# Extensions explicitly blocked regardless of claimed MIME type.
BLOCKED_EXTENSIONS = {
    ".exe", ".sh", ".bat", ".cmd", ".ps1", ".dll", ".so",
    ".bin", ".msi", ".jar", ".app", ".apk", ".ipa",
    ".js", ".ts", ".py", ".rb", ".pl", ".php",
    ".html", ".htm", ".svg",
}

# MIME → allowed extensions map (extra guard).
MIME_TO_EXTENSIONS: dict[str, set[str]] = {
    "application/pdf": {".pdf"},
    "image/jpeg": {".jpg", ".jpeg"},
    "image/jpg": {".jpg", ".jpeg"},
    "image/png": {".png"},
}


def _sanitize_filename(name: str) -> str:
    """Remove path traversal sequences and non-safe characters."""
    # Strip directory components
    name = os.path.basename(name)
    # Replace anything not alphanumeric, dot, hyphen, or underscore
    name = re.sub(r"[^\w.\-]", "_", name)
    # Prevent double dots (e.g. ../../)
    name = re.sub(r"\.{2,}", ".", name)
    return name or "document"


def _validate_upload(filename: str, mime_type: str, data: bytes) -> None:
    """Raise ValueError if the upload is unsafe or unsupported."""
    if len(data) > MAX_FILE_SIZE_BYTES:
        raise ValueError(
            f"File exceeds maximum allowed size of {MAX_FILE_SIZE_BYTES // (1024*1024)} MB."
        )

    if mime_type not in ALLOWED_MIME_TYPES:
        raise ValueError(
            f"MIME type '{mime_type}' is not allowed. "
            f"Allowed: {', '.join(sorted(ALLOWED_MIME_TYPES))}"
        )

    ext = Path(filename).suffix.lower()
    if ext in BLOCKED_EXTENSIONS:
        raise ValueError(f"File extension '{ext}' is not permitted.")

    allowed_exts = MIME_TO_EXTENSIONS.get(mime_type, set())
    if allowed_exts and ext not in allowed_exts:
        raise ValueError(
            f"Extension '{ext}' does not match declared MIME type '{mime_type}'."
        )


class DocumentStorageService(ABC):
    """Abstract storage interface. Swap implementations freely."""

    @abstractmethod
    def save(
        self,
        user_id: str,
        filename: str,
        mime_type: str,
        data: bytes,
        document_type: str,
        category: str,
    ) -> DocumentMetadata:
        """Validate, persist, and return metadata. Never exposes storage path."""

    @abstractmethod
    def list(self, user_id: str) -> list[DocumentMetadata]:
        """List all documents for a user."""

    @abstractmethod
    def get_metadata(self, user_id: str, document_id: str) -> Optional[DocumentMetadata]:
        """Return metadata for a single document, or None if not found."""

    @abstractmethod
    def read(self, user_id: str, document_id: str) -> Optional[tuple[bytes, str]]:
        """Return (bytes, mime_type) for download, or None if not found."""

    @abstractmethod
    def delete(self, user_id: str, document_id: str) -> bool:
        """Delete document and metadata. Returns True if deleted."""


class LocalDocumentStorage(DocumentStorageService):
    """
    Development storage: files in data/secure_uploads/<user_id>/<doc_id>.<ext>
    Metadata in data/secure_uploads/<user_id>/metadata.json

    NOT suitable for production at scale, but the interface means production
    uses the same API routes with a different implementation injected.
    """

    def __init__(self, base_dir: Optional[Path] = None) -> None:
        if base_dir is None:
            env_dir = os.environ.get("PERSISTENT_DATA_DIR")
            if env_dir:
                base_dir = Path(env_dir) / "secure_uploads"
            else:
                base_dir = Path(__file__).parent.parent.parent / "data" / "secure_uploads"
        self._base = base_dir
        self._base.mkdir(parents=True, exist_ok=True)

    def _user_dir(self, user_id: str) -> Path:
        # Sanitize user_id to prevent path traversal
        safe_id = re.sub(r"[^\w\-]", "", user_id)[:64]
        d = self._base / safe_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _meta_path(self, user_id: str) -> Path:
        return self._user_dir(user_id) / "metadata.json"

    def _load_meta(self, user_id: str) -> dict[str, dict]:
        path = self._meta_path(user_id)
        if not path.exists():
            return {}
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def _save_meta(self, user_id: str, meta: dict[str, dict]) -> None:
        with open(self._meta_path(user_id), "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)

    def save(
        self,
        user_id: str,
        filename: str,
        mime_type: str,
        data: bytes,
        document_type: str,
        category: str,
    ) -> DocumentMetadata:
        _validate_upload(filename, mime_type, data)

        safe_name = _sanitize_filename(filename)
        ext = Path(safe_name).suffix.lower() or ".bin"
        doc_id = str(uuid.uuid4())

        # Store with an opaque name to prevent direct guessing.
        storage_name = f"{doc_id}{ext}"
        file_path = self._user_dir(user_id) / storage_name

        with open(file_path, "wb") as f:
            f.write(data)

        meta = DocumentMetadata(
            id=doc_id,
            user_id=user_id,
            documentType=document_type,
            category=category,
            originalFileName=safe_name,
            mimeType=mime_type,
            fileSizeBytes=len(data),
        )

        all_meta = self._load_meta(user_id)
        all_meta[doc_id] = meta.model_dump()
        self._save_meta(user_id, all_meta)

        return meta

    def list(self, user_id: str) -> list[DocumentMetadata]:
        return [
            DocumentMetadata(**v)
            for v in self._load_meta(user_id).values()
        ]

    def get_metadata(self, user_id: str, document_id: str) -> Optional[DocumentMetadata]:
        data = self._load_meta(user_id).get(document_id)
        return DocumentMetadata(**data) if data else None

    def read(self, user_id: str, document_id: str) -> Optional[tuple[bytes, str]]:
        meta = self.get_metadata(user_id, document_id)
        if not meta:
            return None
        ext = Path(meta.originalFileName).suffix.lower() or ".bin"
        file_path = self._user_dir(user_id) / f"{document_id}{ext}"
        if not file_path.exists():
            return None
        with open(file_path, "rb") as f:
            return f.read(), meta.mimeType

    def delete(self, user_id: str, document_id: str) -> bool:
        meta = self.get_metadata(user_id, document_id)
        if not meta:
            return False
        ext = Path(meta.originalFileName).suffix.lower() or ".bin"
        file_path = self._user_dir(user_id) / f"{document_id}{ext}"
        if file_path.exists():
            file_path.unlink()
        all_meta = self._load_meta(user_id)
        all_meta.pop(document_id, None)
        self._save_meta(user_id, all_meta)
        return True


# ---------------------------------------------------------------------------
# Profile persistence (simple JSON store for development)
# ---------------------------------------------------------------------------

class ProfileStore:
    """
    Simple JSON-based profile store for development.
    In production, replace with a proper database (PostgreSQL, Firestore, etc.).
    """

    def __init__(self, base_dir: Optional[Path] = None) -> None:
        if base_dir is None:
            env_dir = os.environ.get("PERSISTENT_DATA_DIR")
            if env_dir:
                base_dir = Path(env_dir) / "profiles"
            else:
                base_dir = Path(__file__).parent.parent.parent / "data" / "profiles"
        self._base = base_dir
        self._base.mkdir(parents=True, exist_ok=True)

    def _path(self, user_id: str) -> Path:
        safe_id = re.sub(r"[^\w\-]", "", user_id)[:64]
        return self._base / f"{safe_id}.json"

    def get(self, user_id: str) -> Optional[dict]:
        path = self._path(user_id)
        if not path.exists():
            return None
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def upsert(self, user_id: str, data: dict) -> dict:
        from datetime import datetime, timezone
        import uuid
        existing = self.get(user_id) or {}
        existing.update(data)
        existing["user_id"] = user_id
        existing["updatedAt"] = datetime.now(timezone.utc).isoformat()
        if "createdAt" not in existing:
            existing["createdAt"] = existing["updatedAt"]
        # Always ensure a stable id is present
        if "id" not in existing:
            existing["id"] = str(uuid.uuid4())
        with open(self._path(user_id), "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2)
        return existing


# Module-level singletons (swappable in tests via dependency injection)
_storage: Optional[DocumentStorageService] = None
_profile_store: Optional[ProfileStore] = None


def get_document_storage() -> DocumentStorageService:
    global _storage
    if _storage is None:
        _storage = LocalDocumentStorage()
    return _storage


def get_profile_store() -> ProfileStore:
    global _profile_store
    if _profile_store is None:
        _profile_store = ProfileStore()
    return _profile_store
