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

"""Unit tests for GCP Knowledge Catalog tools and MCP integration."""

from app.tools import (
    attach_or_update_tag,
    get_entry_metadata,
    list_asset_tags,
    mcp_knowledge_catalog_query,
    search_catalog,
)


def test_search_catalog() -> None:
    """Test searching data assets in Knowledge Catalog."""
    res = search_catalog(query="transactions")
    assert res["status"] == "success"
    assert res["total_results"] > 0
    assert any("transactions" in a["display_name"].lower() for a in res["results"])


def test_get_entry_metadata() -> None:
    """Test fetching metadata and schema for a data asset."""
    res = get_entry_metadata(entry_name="transactions_prod")
    assert res["status"] == "success"
    assert "schema" in res
    assert len(res["schema"]["columns"]) > 0


def test_list_asset_tags() -> None:
    """Test listing attached governance tags."""
    res = list_asset_tags(entry_name="customer_profiles")
    assert res["status"] == "success"
    assert "tags" in res


def test_attach_or_update_tag() -> None:
    """Test attaching a governance tag to an asset."""
    res = attach_or_update_tag(
        entry_name="customer_profiles",
        tag_template_display_name="Data Governance",
        tag_fields={"classification": "Restricted", "data_owner": "security-lead@example.com"}
    )
    assert res["status"] == "success"
    assert res["tag_template"] == "Data Governance"


def test_mcp_knowledge_catalog_query() -> None:
    """Test invoking Knowledge Catalog MCP tools."""
    res = mcp_knowledge_catalog_query(
        tool_name="search_data_assets",
        parameters={"query": "customer"}
    )
    assert res["status"] == "success"
    assert res["protocol"] == "MCP/1.0"
    assert "result" in res
