# tests/test_search.py
"""
Search API tests
"""

import pytest
from fastapi.testclient import TestClient

def test_search_empty_query(client: TestClient, auth_headers):
    """Test search with empty query."""
    response = client.get("/api/search/?q=", headers=auth_headers)
    
    assert response.status_code == 422  # Validation error

def test_search_valid_query(client: TestClient, auth_headers):
    """Test search with valid query."""
    response = client.get("/api/search/?q=test", headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert "total" in data
    assert data["query"] == "test"

def test_search_suggestions(client: TestClient, auth_headers):
    """Test search suggestions."""
    response = client.get("/api/search/suggestions?q=te", headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert "suggestions" in data
    assert isinstance(data["suggestions"], list)