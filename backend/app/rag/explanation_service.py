"""
app/rag/explanation_service.py
──────────────────────────────
Grounded Explanation Service — Phase 3.

Architecture:
    RankedRecommendations (from deterministic engines)
        │
        ├── ExplanationContextBuilder → immutable facts dict
        │
        └── retrieve_scheme_context() → verified knowledge chunks
        │
        ▼
    GroundedPromptBuilder
        │
        ├── Deterministic facts (MUST NOT be changed by LLM)
        ├── Retrieved scheme knowledge
        ├── Allowed citation registry (derived from chunks)
        ├── Required output language
        └── Strict JSON output schema
        │
        ▼
    LiteLLM (model/provider from environment: LLM_MODEL / LLM_API_KEY)
        │
        ▼
    JSON Validation (Pydantic)
        │
        ▼
    Citation Validation (allowed set check)
        │
        ▼
    ExplanationResponse

The LLM ONLY explains. It NEVER changes eligibility, recommendation score,
scheme ranking, or financial figures.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import litellm

from app.rag.retriever import RetrievedChunk
from app.recommendation_engine import ScoredScheme
from app.schemas.explanation import (
    ExplanationResponse,
    GroundingStatus,
    SourceCitation,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration (from environment; no hardcoded defaults for model name)
# ---------------------------------------------------------------------------

def _llm_model() -> str:
    model = os.environ.get("LLM_MODEL")
    if not model:
        raise RuntimeError(
            "LLM_MODEL environment variable is not set. "
            "Set it to a litellm-compatible model string such as "
            "'gemini/gemini-1.5-pro', 'gpt-4o', 'claude-3-5-sonnet-20241022', etc."
        )
    return model


# ---------------------------------------------------------------------------
# ExplanationContextBuilder
# ---------------------------------------------------------------------------

def build_explanation_context(top: ScoredScheme) -> dict[str, Any]:
    """
    Deterministically extracts the immutable facts from the top recommendation.

    The LLM receives this dict and MUST explain these facts as-is.
    It must not recalculate, rerank, or reinterpret any value here.
    """
    return {
        "scheme_id": top.scheme_id,
        "scheme_name": top.scheme_name,
        "eligibility_status": top.eligibility_status,
        "recommendation_score": top.recommendation_score,
        "eligibility_reason_codes": top.eligibility_reason_codes,
        "action_required_reason_codes": top.action_required_reason_codes,
        "financial_assessment": top.financial_assessment,
    }


# ---------------------------------------------------------------------------
# Allowed citation registry (built deterministically from retrieved chunks)
# ---------------------------------------------------------------------------

def _build_allowed_citations(chunks: list[RetrievedChunk]) -> list[dict[str, str]]:
    """Returns the set of citations the LLM is permitted to produce.
    
    Derived purely from the retrieved chunks — no LLM involvement.
    """
    seen: set[tuple[str, str]] = set()
    allowed: list[dict[str, str]] = []
    for rc in chunks:
        key = (rc.chunk.source_id, rc.chunk.section)
        if key not in seen:
            seen.add(key)
            allowed.append({"source_id": rc.chunk.source_id, "section": rc.chunk.section})
    return allowed


# ---------------------------------------------------------------------------
# Prompt Builder
# ---------------------------------------------------------------------------

_OUTPUT_SCHEMA = """
{
  "language": "<language_code>",
  "scheme_id": "<must_match_facts.scheme_id exactly>",
  "scheme_name": "<must_match_facts.scheme_name exactly>",
  "summary": "<maximum 2-3 concise sentences in the requested language>",
  "why_recommended": ["<reason 1>", "<reason 2>", "<reason 3> (maximum 3 items)"],
  "important_conditions": ["<condition 1>", "<condition 2>", "<condition 3> (maximum 3 items)"],
  "next_steps": ["<step 1>", "<step 2>", "<step 3> (maximum 3 items)"],
  "citations": [
    {"source_id": "<only actually used sources>", "section": "<only actually used sources>"}
  ],
  "grounding_status": "GROUNDED"
}
"""


def _build_prompt(
    facts: dict[str, Any],
    chunks: list[RetrievedChunk],
    allowed_citations: list[dict[str, str]],
    language: str,
) -> list[dict[str, str]]:
    """Builds the LiteLLM message list (system + user)."""

    # Part A: System — short, firm rules only
    system_prompt = f"""You are a financial assistance explanation engine for SAARTHI, a government scheme recommender system for Scheduled Caste beneficiaries in India.

RULES (follow exactly, no exceptions):
1. DETERMINISTIC FACTS are fixed. Do NOT change scheme_id, scheme_name, eligibility_status, scores, or reason codes.
2. The top recommended scheme is FINAL. Do NOT suggest or prefer any other scheme.
3. Only state facts explicitly present in the RETRIEVED KNOWLEDGE. Never invent or estimate: interest rates, loan limits, income limits, financing percentages, repayment periods, moratorium periods, or project cost limits.
4. Citations must come ONLY from ALLOWED CITATIONS. Never invent source_id or section values.
5. Respond in language '{language}'. JSON keys stay in English. All explanation text in '{language}'.
6. Return ONLY a valid JSON object immediately. Do not write any internal thought process, reasoning, or prose outside the JSON."""

    # Part B: User — the actual context and task
    retrieved_text = ""
    for i, rc in enumerate(chunks, 1):
        retrieved_text += f"\n--- SOURCE {i} ---\n"
        retrieved_text += f"Scheme: {rc.chunk.scheme_name}\n"
        retrieved_text += f"Section: {rc.chunk.section}\n"
        retrieved_text += f"source_id: {rc.chunk.source_id}\n"
        retrieved_text += f"Content:\n{rc.chunk.text}\n"

    user_prompt = f"""DETERMINISTIC FACTS (do not change):
{json.dumps(facts, indent=2, ensure_ascii=False)}

RETRIEVED SCHEME KNOWLEDGE (only source; never invent: Interest rates, Loan amounts, Income eligibility limits, Financing percentages, Repayment periods, Moratorium periods, Project cost limits):
{retrieved_text}
ALLOWED CITATIONS (use only these; do not invent):
{json.dumps(allowed_citations, ensure_ascii=False)}

REQUESTED LANGUAGE: {language}

OUTPUT SCHEMA:
{_OUTPUT_SCHEMA}

Return only the JSON now."""

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


# ---------------------------------------------------------------------------
# Citation validation
# ---------------------------------------------------------------------------

def _validate_citations(
    generated: list[SourceCitation],
    allowed: list[dict[str, str]],
) -> list[SourceCitation]:
    """
    Retains only citations that exist in the allowed set.
    Invented or hallucinated citations are silently removed.
    This is the final hard filter on LLM output.
    """
    allowed_set = {(c["source_id"], c["section"]) for c in allowed}
    return [c for c in generated if (c.source_id, c.section) in allowed_set]


# ---------------------------------------------------------------------------
# Core service function
# ---------------------------------------------------------------------------

def generate_explanation(
    top: ScoredScheme,
    retrieved_chunks: list[RetrievedChunk],
    language: str,
) -> ExplanationResponse:
    """
    Produces a grounded, structured explanation for the top recommendation.

    Args:
        top: The deterministic top recommendation from the recommendation engine.
        retrieved_chunks: Scheme context chunks from retrieve_scheme_context().
        language: BCP-47 language code (e.g., "hi", "en").

    Returns:
        ExplanationResponse with grounding_status:
        - GROUNDED if a valid, cited explanation was produced.
        - INSUFFICIENT_CONTEXT if no chunks were available.
        - REFUSED if the LLM failed to produce valid JSON after one retry.
    """
    # Fast fail — do not call the LLM if there is no context to ground on.
    if not retrieved_chunks:
        logger.warning(
            "No retrieved chunks for scheme %s — returning INSUFFICIENT_CONTEXT.",
            top.scheme_id,
        )
        return ExplanationResponse.insufficient_context(
            language=language,
            scheme_id=top.scheme_id,
            scheme_name=top.scheme_name,
        )

    facts = build_explanation_context(top)
    allowed_citations = _build_allowed_citations(retrieved_chunks)
    messages = _build_prompt(facts, retrieved_chunks, allowed_citations, language)
    model = _llm_model()

    # Attempt 1, then 1 retry with an explicit JSON correction message.
    raw_response: str | None = None
    for attempt in range(2):
        try:
            if attempt == 1:
                # Retry: append a correction message asking strictly for JSON
                messages = messages + [
                    {
                        "role": "user",
                        "content": (
                            "Your previous response was not valid JSON. "
                            "Return ONLY the raw JSON object with no surrounding text, "
                            "prose, or code fences."
                        ),
                    }
                ]

            response = litellm.completion(
                model=model,
                messages=messages,
                temperature=0.1,
                max_tokens=2048,  # Confirmed working limit for Sarvam-105b
                extra_body={"reasoning_effort": None},  # Disables reasoning to avoid exhausting tokens
            )

            # Guard: if the model hit the output token limit, content will be None or incomplete.
            finish_reason = response.choices[0].finish_reason
            if finish_reason == "length":
                logger.warning(
                    "LLM output truncated (finish_reason=length) on attempt %d for scheme %s."
                    " Treating as parse failure.",
                    attempt + 1,
                    top.scheme_id,
                )
                raise ValueError("LLM output truncated: finish_reason=length")

            raw_response = response.choices[0].message.content or ""

            # Strip potential code fences before parsing
            cleaned = raw_response.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("```")[1]
                if cleaned.startswith("json"):
                    cleaned = cleaned[4:]
            cleaned = cleaned.strip()

            parsed = json.loads(cleaned)

            # Validate schema via Pydantic
            explanation = ExplanationResponse.model_validate(parsed)

            # Enforce scheme_id immutability — LLM must not override the deterministic result
            if explanation.scheme_id != top.scheme_id:
                logger.warning(
                    "LLM attempted to change scheme_id from %s to %s. Reverting.",
                    top.scheme_id,
                    explanation.scheme_id,
                )
                explanation = ExplanationResponse(
                    **{
                        **explanation.model_dump(),
                        "scheme_id": top.scheme_id,
                        "scheme_name": top.scheme_name,
                    }
                )

            # Validate and strip hallucinated citations
            validated_citations = _validate_citations(explanation.citations, allowed_citations)
            if len(validated_citations) < len(explanation.citations):
                logger.warning(
                    "Removed %d hallucinated citation(s) from LLM output for scheme %s.",
                    len(explanation.citations) - len(validated_citations),
                    top.scheme_id,
                )

            return ExplanationResponse(
                **{
                    **explanation.model_dump(),
                    "citations": validated_citations,
                    "grounding_status": GroundingStatus.GROUNDED,
                }
            )

        except (json.JSONDecodeError, Exception) as exc:
            logger.warning(
                "Explanation generation attempt %d failed for scheme %s: %s",
                attempt + 1,
                top.scheme_id,
                exc,
            )

    # Both attempts failed — return a safe REFUSED response
    logger.error(
        "All explanation attempts failed for scheme %s. Returning REFUSED.",
        top.scheme_id,
    )
    return ExplanationResponse.refused(
        language=language,
        scheme_id=top.scheme_id,
        scheme_name=top.scheme_name,
    )
