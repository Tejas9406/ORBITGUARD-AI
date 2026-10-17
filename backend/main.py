"""
SatShield & OrbitGuard AI - Main Application Entrypoint
Exposes the complete FastAPI app with full /api/v1/* routes and telemetry endpoints.
"""
from backend.api import app

__all__ = ["app"]
