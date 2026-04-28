"""
app/api/router.py
──────────────────
Central router that registers all sub-routers.
main.py only touches this file — never individual route modules.
"""

from fastapi import APIRouter
from app.api.routes import evaluation, health, query, rag, schema

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(query.router)
api_router.include_router(schema.router)
api_router.include_router(rag.router)
api_router.include_router(evaluation.router)
