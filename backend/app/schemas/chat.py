from pydantic import BaseModel, Field, field_validator
from typing import Optional
from enum import Enum

from app.api.router import ApplicantProfile
from app.schemas.explanation import SourceCitation, GroundingStatus

class ResponseSource(str, Enum):
    RAG_LLM = "RAG_LLM"
    DETERMINISTIC_FALLBACK = "DETERMINISTIC_FALLBACK"
    DOMAIN_FALLBACK = "DOMAIN_FALLBACK"
    CLARIFICATION = "CLARIFICATION"

class ConversationState(str, Enum):
    INITIAL_QUERY = "INITIAL_QUERY"
    COLLECTING_ACTIVITY = "COLLECTING_ACTIVITY"
    COLLECTING_ELIGIBILITY = "COLLECTING_ELIGIBILITY"
    COLLECTING_LOCATION = "COLLECTING_LOCATION"
    COLLECTING_BUSINESS_STATUS = "COLLECTING_BUSINESS_STATUS"
    COLLECTING_FUNDING = "COLLECTING_FUNDING"
    COLLECTING_PROJECT_COST = "COLLECTING_PROJECT_COST"
    SCHEME_RECOMMENDATION = "SCHEME_RECOMMENDATION"
    DOCUMENT_PREPARATION = "DOCUMENT_PREPARATION"
    PARTNER_SEARCH = "PARTNER_SEARCH"
    PARTNER_SELECTION = "PARTNER_SELECTION"
    APPLICATION_GUIDANCE = "APPLICATION_GUIDANCE"
    COMPLETED = "COMPLETED"

class ChatProfile(BaseModel):
    projectType: Optional[str] = None
    estimatedProjectCost: Optional[int] = Field(None, ge=0)
    annualFamilyIncome: Optional[int] = Field(None, ge=0)
    educationStatus: Optional[str] = None
    gender: Optional[str] = None
    age: Optional[int] = None
    isUrban: Optional[bool] = None
    stateCode: Optional[str] = None
    districtCode: Optional[str] = None
    activity: Optional[str] = None
    pinCode: Optional[str] = None
    fullName: Optional[str] = None
    scEligibilityStatus: Optional[bool] = None
    existingBusiness: Optional[bool] = None
    fundingRequired: Optional[int] = Field(None, ge=0)
    preferredLanguage: Optional[str] = None
    conversationState: Optional[ConversationState] = None
    recommendedSchemeId: Optional[str] = None
    channelPartnerRequired: Optional[bool] = None

class ChatRequest(BaseModel):
    model_config = {"populate_by_name": True}

    query: str = Field(..., description="The user's free-form chat query.")
    scheme_id_filter: Optional[str] = Field(None, description="Optional scheme ID to restrict search.")
    profile: Optional[ChatProfile] = Field(None, description="Optional applicant profile for contextual eligibility.")
    language: Optional[str] = Field(None, description="Optional preferred language (e.g., 'hi', 'en').")
    conversation_id: Optional[str] = Field(
        default=None,
        alias="sessionId",
        description="Conversation / session identifier. Sent as 'sessionId' from the frontend; "
                    "internally accessed as conversation_id for backward compatibility.",
    )
    user_id: Optional[str] = Field(None, description="The user's persistent device ID")
    guideMe: Optional[bool] = Field(None, description="Optional flag to force the guided journey.")

    @field_validator('query')
    @classmethod
    def query_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Query cannot be empty')
        return v

from app.schemas.assistant import FrontendCitation, AssistantUICard

class ChatResponse(BaseModel):
    answer: str = Field(..., description="The generated conversational answer.")
    language: str = Field(..., description="The detected or requested language used for the answer.")
    citations: list[FrontendCitation] = Field(default_factory=list, description="List of sources cited in the answer.")
    ui_cards: list[AssistantUICard] = Field(default_factory=list, description="List of UI Cards to render.")
    grounding_status: GroundingStatus = Field(..., description="The grounding status of the response.")
    related_scheme_ids: list[str] = Field(default_factory=list, description="List of scheme IDs related to the answer.")
    response_source: ResponseSource = Field(default=ResponseSource.RAG_LLM, description="The source that generated the response.")
    expected_field: Optional[str] = Field(None, description="The Guided Journey field currently being collected (pinCode, existingBusiness, estimatedProjectCost, general).")
