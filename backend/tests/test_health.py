"""
tests/test_health.py
─────────────────────
Unit tests for the health and schema endpoints.
Uses TestClient so no real server is needed.
"""

import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


# ──────────────────────────────────────────────
# Health
# ──────────────────────────────────────────────

def test_root_returns_200():
    resp = client.get("/")
    assert resp.status_code == 200
    assert "running" in resp.json()["message"].lower()


def test_liveness_check():
    resp = client.get("/api/v1/health/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["version"] is not None
    assert any(c["name"] == "api" for c in data["components"])


def test_full_health_returns_components():
    resp = client.get("/api/v1/health/full")
    assert resp.status_code == 200
    data = resp.json()
    component_names = [c["name"] for c in data["components"]]
    assert "api" in component_names
    assert "ollama" in component_names
    assert "databases" in component_names
    assert "rag_index" in component_names


# ──────────────────────────────────────────────
# Schema
# ──────────────────────────────────────────────

def test_list_databases_returns_list():
    resp = client.get("/api/v1/schema/databases")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_unknown_database_returns_404():
    resp = client.get("/api/v1/schema/this_db_does_not_exist_xyz")
    assert resp.status_code == 404


# ──────────────────────────────────────────────
# RAG status
# ──────────────────────────────────────────────

def test_rag_status_returns_ready_field():
    resp = client.get("/api/v1/rag/status")
    assert resp.status_code == 200
    assert "ready" in resp.json()
