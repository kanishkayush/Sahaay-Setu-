"""
app/schemas/explanation.py
──────────────────────────
Pydantic models for the POST /v1/explanations request and response.

The response schema is the strict contract the LLM must satisfy.
The service will validate every generated response against this model
before returning it to the caller.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Shared / nested models
# ---------------------------------------------------------------------------

class GroundingStatus(str, Enum):
    """Whether the explanation is grounded in retrieved knowledge.
    
    GROUNDED            — LLM produced a valid explanation supported by
                          retrieved chunks with valid citations.
    INSUFFICIENT_CONTEXT — The retriever returned no chunks for the scheme,
                          so the LLM was never called. The explanation fields
                          will be empty.
    REFUSED             — The LLM was called but returned invalid/unparseable
                          JSON after a single retry. Safe fallback returned.
    """
    GROUNDED = "GROUNDED"
    INSUFFICIENT_CONTEXT = "INSUFFICIENT_CONTEXT"
    REFUSED = "REFUSED"


class SourceCitation(BaseModel):
    """A single citation produced by the LLM and validated against allowed citations."""
    source_id: str
    section: str


# ---------------------------------------------------------------------------
# Request
# ---------------------------------------------------------------------------

class ExplanationRequest(BaseModel):
    """
    Stateless explanation request.

    Contains the full applicant profile so the explanation service can
    run eligibility + recommendation internally, then explain the result.
    The profile structure mirrors ApplicantProfile in router.py.
    """
    profile: dict  # Forward-compatible; the router layer validates the profile.
    language: str = Field(default="en", pattern="^(en|hi|mr|bn|ta|te)$")


# ---------------------------------------------------------------------------
# Response
# ---------------------------------------------------------------------------

class ExplanationResponse(BaseModel):
    """
    The structured, validated explanation returned to the frontend.

    The LLM must produce every field. The service validates:
    1. JSON parsability.
    2. Schema conformance (this Pydantic model).
    3. Citation validity (every citation must be in the allowed set derived
       from retrieved chunks).
    4. scheme_id immutability (must match the deterministic top recommendation).
    """
    language: str
    scheme_id: str
    scheme_name: str
    summary: str
    why_recommended: list[str]
    important_conditions: list[str]
    next_steps: list[str]
    citations: list[SourceCitation]
    grounding_status: GroundingStatus

    @classmethod
    def refused(cls, language: str, scheme_id: str = "", scheme_name: str = "") -> "ExplanationResponse":
        """Canonical safe fallback when the LLM fails or produces invalid output."""
        return cls(
            language=language,
            scheme_id=scheme_id,
            scheme_name=scheme_name,
            summary="",
            why_recommended=[],
            important_conditions=[],
            next_steps=[],
            citations=[],
            grounding_status=GroundingStatus.REFUSED,
        )

    @classmethod
    def insufficient_context(cls, language: str, scheme_id: str, scheme_name: str) -> "ExplanationResponse":
        """Returned when the retriever found no chunks for the scheme."""
        return cls(
            language=language,
            scheme_id=scheme_id,
            scheme_name=scheme_name,
            summary="",
            why_recommended=[],
            important_conditions=[],
            next_steps=[],
            citations=[],
            grounding_status=GroundingStatus.INSUFFICIENT_CONTEXT,
        )
