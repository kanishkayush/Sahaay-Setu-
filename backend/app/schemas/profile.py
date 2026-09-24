"""
app/schemas/profile.py
──────────────────────
Persistent User Profile and Document Vault schemas.

The user_id is a device-generated UUID for the development phase.
In production, this is replaced by the authenticated user ID from
the auth middleware — no other code changes required.

Architecture:
  PersistentUserProfile  ← long-lived, survives across multiple loan journeys
  LoanApplicationProfile ← ephemeral, application-specific (one per loan journey)
  DocumentMetadata       ← file upload metadata, linked to user_id

Security notes:
  - Raw storage paths are NEVER returned in API responses.
  - Document content is never sent to the LLM.
  - This schema does not store Aadhaar/PAN numbers.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field
import uuid


class GeoPoint(BaseModel):
    latitude: float
    longitude: float

class ProfileAddress(BaseModel):
    state: Optional[str] = None
    district: Optional[str] = None
    city: Optional[str] = None
    pinCode: Optional[str] = None
    addressLine1: Optional[str] = None
    coordinates: Optional[GeoPoint] = None


class ProfileEligibility(BaseModel):
    scEligibilityStatus: Optional[bool] = None
    annualFamilyIncome: Optional[int] = Field(None, ge=0)


class ProfileBusiness(BaseModel):
    existingBusiness: Optional[bool] = None
    businessActivity: Optional[str] = None


class ProfilePreferences(BaseModel):
    language: str = "en"


class PersistentUserProfile(BaseModel):
    """
    Long-lived profile for a SAARTHI user.

    Distinct from ChatProfile (ephemeral, per-conversation) and
    LoanApplicationProfile (ephemeral, per-application).
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str  # Device-generated UUID; replaced by auth UID in production

    # Personal information
    fullName: Optional[str] = None
    phoneNumber: Optional[str] = None
    email: Optional[str] = None
    dateOfBirth: Optional[str] = None  # ISO-8601 date string

    # Location
    address: ProfileAddress = Field(default_factory=ProfileAddress)

    # Eligibility
    eligibility: ProfileEligibility = Field(default_factory=ProfileEligibility)

    # Business
    business: ProfileBusiness = Field(default_factory=ProfileBusiness)

    # Preferences
    preferences: ProfilePreferences = Field(default_factory=ProfilePreferences)

    # Timestamps
    createdAt: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updatedAt: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ProfileUpdateRequest(BaseModel):
    """Partial update — only provided fields are written."""
    fullName: Optional[str] = None
    phoneNumber: Optional[str] = None
    email: Optional[str] = None
    dateOfBirth: Optional[str] = None
    address: Optional[ProfileAddress] = None
    eligibility: Optional[ProfileEligibility] = None
    business: Optional[ProfileBusiness] = None
    preferences: Optional[ProfilePreferences] = None


# ---------------------------------------------------------------------------
# Document Vault
# ---------------------------------------------------------------------------

class DocumentCategory(str):
    IDENTITY = "IDENTITY"
    ELIGIBILITY = "ELIGIBILITY"
    FINANCIAL = "FINANCIAL"
    BUSINESS = "BUSINESS"
    OTHER = "OTHER"


ALLOWED_DOCUMENT_CATEGORIES = {
    "IDENTITY", "ELIGIBILITY", "FINANCIAL", "BUSINESS", "OTHER"
}

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/jpg",
    "image/png",
}

# 10 MB upload limit
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024


class DocumentVerificationStatus(str):
    UPLOADED = "UPLOADED"
    VERIFIED = "VERIFIED"
    EXPIRED = "EXPIRED"
    REJECTED = "REJECTED"


class DocumentMetadata(BaseModel):
    """
    Metadata stored for each uploaded document.
    The raw file path is NEVER exposed in this model.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    documentType: str   # e.g. "CASTE_CERTIFICATE", "AADHAAR", "PAN"
    category: str       # One of ALLOWED_DOCUMENT_CATEGORIES
    originalFileName: str
    mimeType: str
    fileSizeBytes: int
    uploadedAt: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    verificationStatus: str = "UPLOADED"
    expiryDate: Optional[str] = None  # ISO-8601 date string
    notes: Optional[str] = None


class DocumentUploadResponse(BaseModel):
    """What the frontend receives after a successful upload."""
    id: str
    documentType: str
    category: str
    originalFileName: str
    mimeType: str
    fileSizeBytes: int
    uploadedAt: str
    verificationStatus: str
    expiryDate: Optional[str] = None
