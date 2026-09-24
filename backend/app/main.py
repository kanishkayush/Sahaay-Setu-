"""
app/main.py
───────────
FastAPI application entry point for the SAARTHI backend.

Run locally:
    uvicorn app.main:app --reload --port 8000

The default port 8000 matches the frontend's default:
    API_BASE_URL = 'http://localhost:8000'   (src/api/config.ts)
"""

import os
from pathlib import Path

# Load .env automatically so `uvicorn app.main:app` works without
# manually exporting variables. override=False means real env vars
# always win (safe for CI and production deployments).
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env", override=False)
except ImportError:
    pass  # python-dotenv is optional; fall back to manually-set env vars

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import router
from app.api.assistant import assistant_router
from app.api.chat import router as chat_router
from app.api.profile import profile_router

# ---------------------------------------------------------------------------
# Production safety guard
# ---------------------------------------------------------------------------
# Mock embeddings produce hash-seeded deterministic vectors with no semantic
# meaning. They are acceptable for testing pipeline mechanics, but must never
# be deployed to production where real RAG retrieval quality is required.
_env = os.environ.get("ENVIRONMENT", "").lower()
_mock = os.environ.get("SAARTHI_MOCK_EMBEDDING", "0")
if _env == "production" and _mock == "1":
    raise RuntimeError(
        "SAARTHI startup aborted: SAARTHI_MOCK_EMBEDDING=1 is set while "
        "ENVIRONMENT=production. Mock embeddings cannot be used in production. "
        "Unset SAARTHI_MOCK_EMBEDDING or set it to 0 before deploying."
    )

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="SAARTHI — NSFDC Scheme Recommender",
    description="Deterministic eligibility and scheme recommendation API for SC beneficiaries.",
    version="0.2.0",
)

# Allow the Expo dev client (any localhost origin) during development.
# Tighten this to the production domain before deployment.
cors_origins_env = os.environ.get("CORS_ORIGINS")
if cors_origins_env is not None:
    allow_origins = [origin.strip() for origin in cors_origins_env.split(",") if origin.strip()]
else:
    # Default to localhost for development. Block wildcard in production unless explicitly requested.
    if _env == "production":
        allow_origins = []
    else:
        allow_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(assistant_router)
app.include_router(chat_router)
app.include_router(profile_router)
