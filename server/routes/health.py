# server/routes/health.py
# GET /api/health — simple liveness check endpoint.
# Inputs:  none
# Outputs: {"status": "ok", "version": "..."}

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()

_VERSION = "1.0.0"


@router.get("/health", tags=["ops"])
def health_check() -> dict:
    """Return service liveness status."""
    return {"status": "ok", "version": _VERSION}
