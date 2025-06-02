"""
Authentication tests
"""

import pytest
from fastapi.testclient import TestClient


def test_register_user(client: TestClient, test_user):
    """Test user registration"""
    response = client.post("/api/auth/register", json=test_user)
    assert response.status_code == 200

    data = response.json()
    assert "access_token" in data
    assert data["username"] == test_user["username"]


def test_login_user(client: TestClient, test_user):
    """Test user login"""
    # First register user
    client.post("/api/auth/register", json=test_user)

    # Then login
    login_data = {
        "username": test_user["username"],
        "password": test_user["password"]
    }
    response = client.post("/api/auth/login", data=login_data)
    assert response.status_code == 200

    data = response.json()
    assert "access_token" in data


def test_invalid_login(client: TestClient):
    """Test invalid login"""
    login_data = {
        "username": "nonexistent",
        "password": "wrongpassword"
    }
    response = client.post("/api/auth/login", data=login_data)
    assert response.status_code == 401
