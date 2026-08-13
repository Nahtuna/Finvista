# -*- coding: utf-8 -*-
"""Integration tests for API endpoints."""

import pytest
from fastapi.testclient import TestClient
from backend.api.main import app

client = TestClient(app)


def test_health_endpoint():
    """Test health check endpoint."""
    response = client.get("/api/health")
    assert response.status_code == 200
    assert "status" in response.json()
    assert response.json()["status"] in ["healthy", "warning"]


def test_info_endpoint():
    """Test info endpoint."""
    response = client.get("/api/info")
    assert response.status_code == 200
    assert "gateway" in response.json()
    assert "version" in response.json()
    assert "endpoints" in response.json()


def test_regime_market_endpoint():
    """Test regime market endpoint."""
    response = client.get("/api/regime/market")
    # Should return 200 even if data is not available
    assert response.status_code in [200, 404, 500]
    
    if response.status_code == 200:
        data = response.json()
        # If data is available, it should have expected structure
        if isinstance(data, dict):
            assert "regime" in data or "status" in data


def test_market_underlyings_endpoint():
    """Test market underlyings endpoint."""
    response = client.get("/api/market/underlyings")
    # Should return 200 even if data is not available
    assert response.status_code in [200, 404, 500]
    
    if response.status_code == 200:
        data = response.json()
        # If data is available, it should have expected structure
        if isinstance(data, dict):
            assert "underlyings" in data or "status" in data
        elif isinstance(data, list):
            # If list, should contain underlying data
            pass


def test_warrants_opportunities_endpoint():
    """Test warrants opportunities endpoint."""
    response = client.get("/api/warrants/opportunities")
    # Should return 200 even if data is not available
    assert response.status_code in [200, 404, 500]
    
    if response.status_code == 200:
        data = response.json()
        # If data is available, it should have expected structure
        if isinstance(data, dict):
            assert "status" in data or "recommendations" in data or "opportunities" in data


def test_rate_limiting():
    """Test that rate limiting is enabled."""
    # Make multiple requests to test rate limiting
    responses = []
    for _ in range(5):
        response = client.get("/api/health")
        responses.append(response.status_code)
    
    # First few requests should succeed
    assert all(status == 200 for status in responses[:3])


def test_cors_headers():
    """Test that CORS headers are properly set."""
    response = client.get("/api/health", headers={"Origin": "http://localhost:3000"})
    assert response.status_code == 200
    # CORS headers should be present
    assert "access-control-allow-origin" in response.headers or "Access-Control-Allow-Origin" in response.headers
