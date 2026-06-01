# -*- coding: utf-8 -*-
"""
🏆 FINVISTA: REST API INTEGRATION TESTS
========================================
Integration tests for the SaaS FastAPI endpoints.
Tests health check, Greeks calculation, credit health (mocked or database check),
authentication, and basic portfolio route validation.
"""

import pytest
import os
import sys
from fastapi.testclient import TestClient

# Ensure sys.path contains the project root directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.api.main import app

client = TestClient(app)

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["status"] == "online"
    assert "gateway" in json_data
    assert "endpoints" in json_data

def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    json_data = response.json()
    assert "status" in json_data
    assert "model_registry" in json_data
    assert "database_layer" in json_data

def test_calculate_greeks_endpoint():
    payload = {
        "underlying_price": 28500.0,
        "strike_price": 25000.0,
        "days_to_maturity": 95,
        "implied_volatility": 0.42,
        "conversion_ratio": 10.0,
        "risk_free_rate": 0.045
    }
    response = client.post("/api/warrants/greeks", json=payload)
    assert response.status_code == 200
    json_data = response.json()
    assert "delta" in json_data
    assert "gamma" in json_data
    assert "vega" in json_data
    assert "theta" in json_data
    assert json_data["moneyness_category"] == "ITM"

def test_calculate_greeks_endpoint_missing_params():
    payload = {
        "strike_price": 25000.0,
        "days_to_maturity": 95,
        "implied_volatility": 0.42,
        "conversion_ratio": 10.0
    }
    response = client.post("/api/warrants/greeks", json=payload)
    assert response.status_code == 422

def test_auth_flow_and_isolation():
    import time
    username = f"test_user_{int(time.time())}"
    register_payload = {
        "username": username,
        "password": "strongtestpassword123"
    }
    reg_response = client.post("/api/auth/register", json=register_payload)
    assert reg_response.status_code == 201
    assert reg_response.json()["status"] == "success"

    login_data = {
        "username": username,
        "password": "strongtestpassword123"
    }
    login_response = client.post("/api/auth/login", data=login_data)
    assert login_response.status_code == 200
    token_data = login_response.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"
    
    token = token_data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    profile_response = client.get("/api/auth/me", headers=headers)
    assert profile_response.status_code == 200
    assert profile_response.json()["username"] == username

    portfolio_response = client.get("/api/portfolio", headers=headers)
    assert portfolio_response.status_code == 200
    portfolio_data = portfolio_response.json()
    assert portfolio_data["cash"] == 100_000_000.0
    assert len(portfolio_data["active_positions"]) == 0

    reset_response = client.post("/api/portfolio/reset", headers=headers)
    assert reset_response.status_code == 200
    assert reset_response.json()["status"] == "success"

def test_auth_unauthorized():
    response = client.get("/api/portfolio")
    assert response.status_code == 401
