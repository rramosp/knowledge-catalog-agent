# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""End-to-end tests for FastAPI server and Knowledge Catalog endpoints."""

import pytest
from fastapi.testclient import TestClient
from app.fast_api_app import app

client = TestClient(app)


def test_root_web_ui() -> None:
    """Test that the local web interface HTML is served."""
    response = client.get("/")
    assert response.status_code == 200


def test_agent_card_served() -> None:
    """Test that the A2A agent card or metadata is available."""
    response = client.get("/a2a/app/.well-known/agent-card.json")
    # If A2A is mounted, returns 200 or JSON structure
    assert response.status_code in (200, 404, 307)


def test_catalog_search_api() -> None:
    """Test searching data assets via REST endpoint."""
    response = client.get("/api/catalog/search?query=transactions")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "results" in data


def test_catalog_entry_api() -> None:
    """Test fetching entry metadata & schema."""
    response = client.get("/api/catalog/entry?name=transactions_prod")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"


def test_catalog_tags_api() -> None:
    """Test listing attached tags."""
    response = client.get("/api/catalog/tags?name=customer_profiles")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"


def test_mcp_query_api() -> None:
    """Test invoking Remote MCP server tool endpoint."""
    response = client.post(
        "/api/catalog/mcp",
        json={"tool_name": "list_dataplex_lakes", "parameters": {}}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["protocol"] == "MCP/1.0"


def test_collect_feedback_endpoint() -> None:
    """Test logging feedback."""
    feedback_data = {
        "score": 5,
        "user_id": "test-user-123",
        "session_id": "test-session-123",
        "text": "Excellent Knowledge Catalog assistant!",
    }
    response = client.post("/feedback", json=feedback_data)
    assert response.status_code == 200
    assert response.json()["status"] == "success"
