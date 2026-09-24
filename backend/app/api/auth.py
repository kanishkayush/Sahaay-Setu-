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


class SendOtpRequest(BaseModel):
    phoneNumber: str


class VerifyOtpRequest(BaseModel):
    phoneNumber: str
    otp: str


class AuthResponse(BaseModel):
    token: str
    userId: str
    phoneNumber: str


@auth_router.post("/send-otp")
def send_otp(request: SendOtpRequest) -> dict[str, str]:
    phone = request.phoneNumber.strip()
    if not phone or len(phone) < 10:
        raise HTTPException(status_code=400, detail="Invalid phone number.")

    # Generate a fixed OTP for development/testing if phone is 9999999999, else generate 6-digit random
    import random
    otp = "123456" if phone == "9999999999" else f"{random.randint(100000, 999999)}"
    
    # Store OTP with 5-minute expiry
    _otp_store[phone] = {
        "otp": otp,
        "expires_at": datetime.now(timezone.utc) + timedelta(minutes=5),
        "attempts": 0
    }
    
    # Normally we would integrate an SMS provider here (e.g. Twilio, MSG91)
    # Since SMS provider is not configured, we print to console.
    print(f"[AUTH] Sending OTP {otp} to {phone}")
    
    return {"status": "success", "message": "OTP sent successfully."}


@auth_router.post("/verify-otp", response_model=AuthResponse)
def verify_otp(request: VerifyOtpRequest) -> AuthResponse:
    phone = request.phoneNumber.strip()
    otp_record = _otp_store.get(phone)
    
    if not otp_record:
        raise HTTPException(status_code=400, detail="No OTP requested for this number.")
        
    if datetime.now(timezone.utc) > otp_record["expires_at"]:
        _otp_store.pop(phone, None)
        raise HTTPException(status_code=400, detail="OTP has expired.")
        
    if otp_record["attempts"] >= 3:
        _otp_store.pop(phone, None)
        raise HTTPException(status_code=400, detail="Too many failed attempts. Request a new OTP.")
        
    if otp_record["otp"] != request.otp.strip():
        otp_record["attempts"] += 1
        raise HTTPException(status_code=400, detail="Invalid OTP.")
        
    # OTP verified! Clear it.
    _otp_store.pop(phone, None)
    
    # Create session
    token = str(uuid.uuid4())
    user_id = str(uuid.uuid5(uuid.NAMESPACE_URL, phone)) # Deterministic ID based on phone
    
    _sessions[token] = {
        "user_id": user_id,
        "phone": phone,
        "expires_at": datetime.now(timezone.utc) + timedelta(days=30)
    }
    
    return AuthResponse(token=token, userId=user_id, phoneNumber=phone)


def verify_token(token: str) -> str:
    """Validate token and return user_id. Raises 401 if invalid."""
    session = _sessions.get(token)
    if not session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    if datetime.now(timezone.utc) > session["expires_at"]:
        _sessions.pop(token, None)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    return session["user_id"]
