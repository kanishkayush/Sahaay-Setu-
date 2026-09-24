from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum
from app.schemas.explanation import SourceCitation

class AssistantProfileContext(BaseModel):
    annualFamilyIncome: Optional[float] = None
    projectType: Optional[str] = None
    stateCode: Optional[str] = None

class AssistantQueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    responseLanguage: str
    sessionId: Optional[str] = None
    guideMe: Optional[bool] = None
    profileContext: Optional[AssistantProfileContext] = None
    history: List[dict] = Field(default_factory=list)

class AssistantActionType(str, Enum):
    OPEN_SCHEME = "OPEN_SCHEME"
    OPEN_PARTNER = "OPEN_PARTNER"
    OPEN_CALCULATOR = "OPEN_CALCULATOR"
    START_RECOMMENDER = "START_RECOMMENDER"
    OPEN_URL = "OPEN_URL"

class AssistantAction(BaseModel):
    type: AssistantActionType
    label: str
    schemeId: Optional[str] = None
    partnerId: Optional[str] = None
    principal: Optional[float] = None
    annualRatePct: Optional[float] = None
    tenureMonths: Optional[int] = None
    url: Optional[str] = None

class AssistantUICardType(str, Enum):
    SCHEME_CARD = "SCHEME_CARD"
    ELIGIBILITY_CARD = "ELIGIBILITY_CARD"
    NEXT_QUESTION_CARD = "NEXT_QUESTION_CARD"
    DOCUMENT_CHECKLIST = "DOCUMENT_CHECKLIST"
    PARTNER_CARD = "PARTNER_CARD"
    APPLICATION_STEP_CARD = "APPLICATION_STEP_CARD"
    WARNING_CARD = "WARNING_CARD"

class AssistantUICard(BaseModel):
    type: AssistantUICardType
    schemeId: Optional[str] = None
    schemeName: Optional[str] = None
    reason: Optional[str] = None
    eligible: Optional[bool] = None
    title: Optional[str] = None
    details: Optional[str] = None
    question: Optional[str] = None
    options: Optional[List[str]] = None
    requiredByScheme: Optional[List[str]] = None
    requiredByPartner: Optional[List[str]] = None
    recommended: Optional[List[str]] = None
    partnerId: Optional[str] = None
    name: Optional[str] = None
    distanceKm: Optional[float] = None
    address: Optional[str] = None
    stepNumber: Optional[int] = None
    description: Optional[str] = None
    message: Optional[str] = None

class FrontendCitation(BaseModel):
    id: str
    title: str
    locator: Optional[str] = None
    url: Optional[str] = None
    snippet: Optional[str] = None
    confidence: Optional[float] = None

class AssistantQueryResponse(BaseModel):
    messageId: str
    answer: str
    answerLanguage: str
    detectedQueryLanguage: Optional[str] = None
    citations: List[FrontendCitation] = Field(default_factory=list)
    suggestedActions: List[AssistantAction] = Field(default_factory=list)
    uiCards: List[Dict[str, Any]] = Field(default_factory=list)
    followUpQuestions: List[str] = Field(default_factory=list)
    grounded: bool = True
    sessionId: Optional[str] = None
    expectedField: Optional[str] = None

class TranscriptionRequest(BaseModel):
    audioBase64: str
    mimeType: str
    language: Optional[str] = None
    sessionId: Optional[str] = None

class TranscriptionResponse(BaseModel):
    text: str
    detectedLanguage: Optional[str] = None
    confidence: Optional[float] = None
    durationMs: Optional[int] = None

