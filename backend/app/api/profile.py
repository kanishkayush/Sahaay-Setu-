"""
app/api/profile.py
──────────────────
GET  /v1/profile              — retrieve persistent user profile
PUT  /v1/profile              — create or update profile (partial update)
GET  /v1/profile/documents    — list all documents for user
POST /v1/profile/documents    — upload a new document
DELETE /v1/profile/documents/{document_id}  — delete a document
GET  /v1/profile/documents/{document_id}/download — authenticated download

The X-User-Id header is used as the user identifier in development.
In production, replace this with the JWT-authenticated user ID from middleware.
"""

from __future__ import annotations

import base64
from typing import Any, Optional

from fastapi import APIRouter, Header, HTTPException, status, UploadFile, File, Form, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import Response
from pydantic import BaseModel

from app.schemas.profile import (
    ALLOWED_DOCUMENT_CATEGORIES,
    ALLOWED_MIME_TYPES,
    DocumentUploadResponse,
    ProfileUpdateRequest,
    PersistentUserProfile,
)
from app.services.storage import get_document_storage, get_profile_store
from app.api.auth import verify_token

profile_router = APIRouter(prefix="/v1", tags=["profile"])
security = HTTPBearer()

# ---------------------------------------------------------------------------
# Helper to extract user_id from headers
# ---------------------------------------------------------------------------

def _require_user_id(
    x_user_id: Optional[str] = Header(None),
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> str:
    """
    Validates the Bearer token to get the user ID.
    If no token is provided, it falls back to X-User-Id for backward compatibility during transition.
    """
    if auth and auth.credentials:
        try:
            return verify_token(auth.credentials)
        except HTTPException:
            pass # Fall back to x_user_id if token is invalid during transition
            
    if not x_user_id or len(x_user_id.strip()) == 0:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Provide a valid Bearer token.",
        )
    return x_user_id.strip()


# ---------------------------------------------------------------------------
# Profile endpoints
# ---------------------------------------------------------------------------

@profile_router.get("/profile")
def get_profile(
    x_user_id: Optional[str] = Header(None),
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> dict[str, Any]:
    user_id = _require_user_id(x_user_id, auth)
    store = get_profile_store()
    profile = store.get(user_id)
    if profile is None:
        # Return an empty profile skeleton — never 404 for a missing profile.
        return PersistentUserProfile(user_id=user_id).model_dump()
    # Backfill id for profiles saved before this field was introduced
    if "id" not in profile:
        profile = store.upsert(user_id, {})  # triggers id generation
    return profile


@profile_router.put("/profile")
def update_profile(
    request: ProfileUpdateRequest,
    x_user_id: Optional[str] = Header(None),
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> dict[str, Any]:
    user_id = _require_user_id(x_user_id, auth)
    store = get_profile_store()

    # Only write non-None fields to avoid overwriting existing data.
    update_data = request.model_dump(exclude_none=True)
    return store.upsert(user_id, update_data)


# ---------------------------------------------------------------------------
# Document endpoints
# ---------------------------------------------------------------------------

class DocumentUploadRequest(BaseModel):
    """Frontend sends base64-encoded file data."""
    filename: str
    mimeType: str
    dataBase64: str
    documentType: str   # e.g. "CASTE_CERTIFICATE", "AADHAAR"
    category: str       # One of ALLOWED_DOCUMENT_CATEGORIES
    expiryDate: Optional[str] = None


@profile_router.get("/profile/documents")
def list_documents(
    x_user_id: Optional[str] = Header(None),
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> dict[str, Any]:
    user_id = _require_user_id(x_user_id, auth)
    storage = get_document_storage()
    docs = storage.list(user_id)
    return {
        "items": [
            DocumentUploadResponse(
                id=d.id,
                documentType=d.documentType,
                category=d.category,
                originalFileName=d.originalFileName,
                mimeType=d.mimeType,
                fileSizeBytes=d.fileSizeBytes,
                uploadedAt=d.uploadedAt,
                verificationStatus=d.verificationStatus,
                expiryDate=d.expiryDate,
            ).model_dump()
            for d in docs
        ]
    }


@profile_router.post("/profile/documents", status_code=status.HTTP_201_CREATED)
def upload_document(
    file: UploadFile = File(...),
    documentType: str = Form(...),
    category: str = Form(...),
    expiryDate: Optional[str] = Form(None),
    x_user_id: Optional[str] = Header(None),
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> dict[str, Any]:
    from fastapi import UploadFile, File, Form
    user_id = _require_user_id(x_user_id, auth)

    # Validate category
    if category not in ALLOWED_DOCUMENT_CATEGORIES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid category '{category}'. Must be one of: {sorted(ALLOWED_DOCUMENT_CATEGORIES)}",
        )

    # Validate MIME type
    mime_type = file.content_type
    if mime_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"MIME type '{mime_type}' is not allowed.",
        )

    try:
        file_data = file.file.read()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Error reading file contents.",
        )

    storage = get_document_storage()
    try:
        meta = storage.save(
            user_id=user_id,
            filename=file.filename,
            mime_type=mime_type,
            data=file_data,
            document_type=documentType,
            category=category,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )

    # Update expiry date if provided
    if expiryDate:
        meta.expiryDate = expiryDate

    return DocumentUploadResponse(
        id=meta.id,
        documentType=meta.documentType,
        category=meta.category,
        originalFileName=meta.originalFileName,
        mimeType=meta.mimeType,
        fileSizeBytes=meta.fileSizeBytes,
        uploadedAt=meta.uploadedAt,
        verificationStatus=meta.verificationStatus,
        expiryDate=meta.expiryDate,
    ).model_dump()


@profile_router.delete("/profile/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: str,
    x_user_id: Optional[str] = Header(None),
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> None:
    user_id = _require_user_id(x_user_id, auth)
    storage = get_document_storage()
    deleted = storage.delete(user_id, document_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )


@profile_router.get("/profile/documents/{document_id}/download")
def download_document(
    document_id: str,
    x_user_id: Optional[str] = Header(None),
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Response:
    """
    Authenticated download. The raw file is served from the backend, never
    via a public static URL. In production, this endpoint would validate a
    JWT and confirm ownership before serving.
    """
    user_id = _require_user_id(x_user_id, auth)
    storage = get_document_storage()

    result = storage.read(user_id, document_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    file_bytes, mime_type = result
    meta = storage.get_metadata(user_id, document_id)
    filename = meta.originalFileName if meta else "document"

    return Response(
        content=file_bytes,
        media_type=mime_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

@profile_router.delete("/profile/clear", status_code=status.HTTP_204_NO_CONTENT)
def clear_profile(
    x_user_id: Optional[str] = Header(None),
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> None:
    """
    Clears all persistent profile data, documents, and memory for the session.
    """
    user_id = _require_user_id(x_user_id, auth)
    
    # 1. Delete all documents
    storage = get_document_storage()
    docs = storage.list(user_id)
    for doc in docs:
        storage.delete(user_id, doc.id)
        
    # 2. Delete profile persistence
    store = get_profile_store()
    path = store._path(user_id)
    if path.exists():
        path.unlink()
        
    # 3. Clear session memory
    from app.rag.memory import clear_session
    clear_session(user_id)
