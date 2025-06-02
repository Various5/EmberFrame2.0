# tests/test_system.py
"""
System API tests
"""

import pytest
from fastapi.testclient import TestClient

def test_health_check(client: TestClient):
    """Test system health check."""
    response = client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] == "healthy"

def test_api_status(client: TestClient):
    """Test API status."""
    response = client.get("/api/status")
    
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "services" in data

def test_admin_stats_unauthorized(client: TestClient, auth_headers):
    """Test admin stats with regular user."""
    response = client.get("/api/system/stats", headers=auth_headers)
    
    assert response.status_code == 403

def test_admin_stats_authorized(client: TestClient, admin_auth_headers):
    """Test admin stats with admin user."""
    response = client.get("/api/system/stats", headers=admin_auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert "cpu_usage" in data
    assert "memory_usage" in data
    assert "user_count" in data