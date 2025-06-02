# tests/test_files.py
"""
File management API tests
"""

import pytest
import io
from fastapi.testclient import TestClient

def test_list_files_empty(client: TestClient, auth_headers):
    """Test listing files when none exist."""
    response = client.get("/api/files/", headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["files"] == []

def test_upload_file(client: TestClient, auth_headers):
    """Test file upload."""
    # Create a test file
    test_content = b"This is a test file content"
    files = {"files": ("test.txt", io.BytesIO(test_content), "text/plain")}
    
    response = client.post(
        "/api/files/upload",
        files=files,
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["uploaded_files"]
    assert len(data["uploaded_files"]) == 1
    assert data["uploaded_files"][0]["name"] == "test.txt"

def test_create_folder(client: TestClient, auth_headers):
    """Test folder creation."""
    response = client.post(
        "/api/files/folder",
        data={"path": "", "name": "TestFolder"},
        headers=auth_headers
    )
    
    assert response.status_code == 200

def test_upload_file_size_limit(client: TestClient, auth_headers):
    """Test file upload size limit."""
    # Create a large file (mock)
    large_content = b"x" * (200 * 1024 * 1024)  # 200MB
    files = {"files": ("large.bin", io.BytesIO(large_content), "application/octet-stream")}
    
    response = client.post(
        "/api/files/upload",
        files=files,
        headers=auth_headers
    )
    
    # Should fail due to size limit
    assert response.status_code in [413, 400]
