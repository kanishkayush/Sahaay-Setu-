"""
app/api/auth.py
───────────────
Authentication router for secure OTP-based login.
"""

from typing import Any, Optional
import uuid
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

auth_router = APIRouter(prefix="/v1/auth", tags=["auth"])

# In-memory store for OTPs (In production, use Redis or DB)
# phone -> {"otp": "123456", "expires_at": datetime, "attempts": 0}
_otp_store = {}

# In-memory store for valid sessions (In production, use Redis or stateless JWT)
# token -> {"user_id": str, "phone": str, "expires_at": datetime}
_sessions = {}


# HACKATHON_AUTH_MODE=true
# Temporary Hackathon Mode: Bypassing Fast2SMS/Twilio OTP verification.
# Only 10-digit mobile number validation is required.

class AuthResponse(BaseModel):
    token: str
    userId: str
    phoneNumber: str

class LoginRequest(BaseModel):
    mobile: str

@auth_router.post("/login", response_model=AuthResponse)
def login(request: LoginRequest) -> AuthResponse:
    phone = request.mobile.strip()
    
    # Normalize Indian phone number
    if phone.startswith("+91"):
        phone = phone[3:]
    elif phone.startswith("0") and len(phone) == 11:
        phone = phone[1:]
        
    phone = "".join([c for c in phone if c.isdigit()])
    
    if len(phone) != 10:
        raise HTTPException(status_code=400, detail="Invalid Indian phone number. Must be 10 digits.")

    normalized_phone = f"+91{phone}"

    # Create session directly without OTP
    token = str(uuid.uuid4())
    user_id = str(uuid.uuid5(uuid.NAMESPACE_URL, normalized_phone)) # Deterministic ID based on phone
    
    _sessions[token] = {
        "user_id": user_id,
        "phone": normalized_phone,
        "expires_at": datetime.now(timezone.utc) + timedelta(days=30)
    }
    
    return AuthResponse(token=token, userId=user_id, phoneNumber=normalized_phone)


def verify_token(token: str) -> str:
    """Validate token and return user_id. Raises 401 if invalid."""
    session = _sessions.get(token)
    if not session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    if datetime.now(timezone.utc) > session["expires_at"]:
        _sessions.pop(token, None)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    return session["user_id"]

from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Header, Depends
import os

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
