"""
app/api/auth.py
───────────────
Authentication router for hackathon login (no OTP).
Any valid Indian 10-digit mobile becomes a stable user identity.
"""

from typing import Optional
import os
import uuid
from fastapi import APIRouter, HTTPException, status, Header, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from app.auth_mobile import normalize_indian_mobile

auth_router = APIRouter(prefix="/v1/auth", tags=["auth"])

# In-memory store for OTPs (In production, use Redis or DB)
_otp_store = {}

# In-memory store for valid sessions (In production, use Redis or stateless JWT)
_sessions = {}


# HACKATHON_AUTH_MODE=true
# Temporary Hackathon Mode: Bypassing Fast2SMS/Twilio OTP verification.
# Any valid Indian mobile (^[6-9][0-9]{9}$) is accepted after normalisation.


class AuthResponse(BaseModel):
    token: str
    userId: str
    phoneNumber: str


class LoginRequest(BaseModel):
    mobile: str


@auth_router.post("/login", response_model=AuthResponse)
def login(request: LoginRequest) -> AuthResponse:
    phone = normalize_indian_mobile(request.mobile)
    if not phone:
        raise HTTPException(
            status_code=400,
            detail="Invalid Indian mobile number. Enter a 10-digit number starting with 6, 7, 8 or 9.",
        )

    normalized_phone = f"+91{phone}"

    # Create session directly without OTP. To avoid fragile in-memory sessions across restarts,
    # we use the deterministic user_id as the token itself.
    user_id = str(uuid.uuid5(uuid.NAMESPACE_URL, normalized_phone))
    token = user_id

    return AuthResponse(token=token, userId=user_id, phoneNumber=normalized_phone)


def verify_token(token: str) -> str:
    """Validate token and return user_id. Raises 401 if invalid."""
    try:
        val = uuid.UUID(token, version=5)
        return str(val)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token format")


security = HTTPBearer(auto_error=False)


def get_current_user_id(
    x_user_id: Optional[str] = Header(None),
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> str:
    """
    Extracts user_id from Bearer token.
    In development, allows fallback to x-user-id header.
    In production, strictly requires a valid Bearer token.
    """
    env = os.getenv("ENVIRONMENT", "development")

    if auth and auth.credentials:
        return verify_token(auth.credentials)

    if env != "production" and x_user_id and x_user_id.strip():
        return x_user_id.strip()

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required. Provide a valid Bearer token.",
    )
