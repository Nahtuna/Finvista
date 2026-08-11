# -*- coding: utf-8 -*-
"""Integration tests for authentication system."""

import pytest
from fastapi.testclient import TestClient
from backend.api.main import app

client = TestClient(app)


def test_register_and_login_flow():
    """Test complete registration and login flow."""
    # Register a new user
    import time
    unique_user = f"user_{int(time.time() * 1000)}"
    register_data = {
        "username": unique_user,
        "password": "SecurePassword123!"
    }
    
    response = client.post("/api/auth/register", json=register_data)
    assert response.status_code == 201
    assert "status" in response.json()
    assert response.json()["status"] == "success"
    
    # Login with the same credentials
    login_data = {
        "username": unique_user,
        "password": "SecurePassword123!"
    }
    
    response = client.post("/api/auth/login", data=login_data)
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"
    
    # Get user profile with token
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    response = client.get("/api/auth/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["username"] == unique_user


def test_register_weak_password():
    """Test that weak passwords are rejected."""
    weak_passwords = [
        ("short", "123456", 422),
        ("no_uppercase", "password123!", 400),
        ("no_lowercase", "PASSWORD123!", 400),
        ("no_digit", "Password!!!!!!", 400),
        ("no_special", "Password12345", 400)
    ]
    
    for test_name, password, expected_status in weak_passwords:
        register_data = {
            "username": f"test_{test_name}",
            "password": password
        }
        
        response = client.post("/api/auth/register", json=register_data)
        assert response.status_code == expected_status
        assert "detail" in response.json()


def test_login_invalid_credentials():
    """Test that invalid credentials are rejected."""
    login_data = {
        "username": "nonexistent_user",
        "password": "WrongPassword123!"
    }
    
    response = client.post("/api/auth/login", data=login_data)
    assert response.status_code == 401
    assert "detail" in response.json()


def test_protected_endpoint_without_token():
    """Test that protected endpoints require authentication."""
    response = client.get("/api/auth/me")
    assert response.status_code == 401
    assert "detail" in response.json()


def test_protected_endpoint_with_invalid_token():
    """Test that protected endpoints reject invalid tokens."""
    headers = {"Authorization": "Bearer invalid_token"}
    response = client.get("/api/auth/me", headers=headers)
    assert response.status_code == 401
    assert "detail" in response.json()
