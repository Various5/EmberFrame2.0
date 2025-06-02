# tests/test_integration.py
"""
Integration tests for full workflows
"""

import pytest
from fastapi.testclient import TestClient
import io

def test_complete_file_workflow(client: TestClient, auth_headers):
    """Test complete file management workflow."""
    
    # 1. Upload a file
    test_content = b"Test file content for workflow"
    files = {"files": ("workflow_test.txt", io.BytesIO(test_content), "text/plain")}
    
    upload_response = client.post(
        "/api/files/upload",
        files=files,
        headers=auth_headers
    )
    
    assert upload_response.status_code == 200
    uploaded_file = upload_response.json()["uploaded_files"][0]
    
    # 2. List files to verify upload
    list_response = client.get("/api/files/", headers=auth_headers)
    assert list_response.status_code == 200
    files_list = list_response.json()["files"]
    assert len(files_list) >= 1
    assert any(f["name"] == "workflow_test.txt" for f in files_list)
    
    # 3. Search for the file
    search_response = client.get("/api/search/?q=workflow", headers=auth_headers)
    assert search_response.status_code == 200
    search_results = search_response.json()["results"]
    assert len(search_results) >= 1
    
    # 4. Download the file
    file_path = uploaded_file["path"]
    download_response = client.get(f"/api/files/download/{file_path}", headers=auth_headers)
    assert download_response.status_code == 200
    
    # 5. Delete the file
    delete_response = client.delete(f"/api/files/{file_path}", headers=auth_headers)
    assert delete_response.status_code == 200

def test_user_registration_and_profile_workflow(client: TestClient):
    """Test user registration and profile management workflow."""
    
    # 1. Register new user
    register_response = client.post(
        "/api/auth/register",
        json={
            "username": "workflowuser",
            "email": "workflow@example.com",
            "password": "workflow123",
            "first_name": "Workflow",
            "last_name": "User"
        }
    )
    
    assert register_response.status_code == 200
    token = register_response.json()["access_token"]
    auth_headers = {"Authorization": f"Bearer {token}"}
    
    # 2. Get profile
    profile_response = client.get("/api/users/me", headers=auth_headers)
    assert profile_response.status_code == 200
    profile = profile_response.json()
    assert profile["username"] == "workflowuser"
    
    # 3. Update profile
    update_response = client.put(
        "/api/users/me",
        json={"first_name": "Updated", "last_name": "Name"},
        headers=auth_headers
    )
    assert update_response.status_code == 200
    
    # 4. Verify update
    updated_profile_response = client.get("/api/users/me", headers=auth_headers)
    assert updated_profile_response.status_code == 200
    updated_profile = updated_profile_response.json()
    assert updated_profile["first_name"] == "Updated"
    assert updated_profile["last_name"] == "Name"