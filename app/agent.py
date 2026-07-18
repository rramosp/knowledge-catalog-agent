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

"""GCP Knowledge Catalog Agent definition for Gemini Enterprise."""

from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import types

from app.tools import (
    attach_or_update_tag,
    get_entry_metadata,
    list_asset_tags,
    mcp_knowledge_catalog_query,
    search_catalog,
)

INSTRUCTION = """You are an expert AI Data Governance Assistant specialized in Google Cloud Platform (GCP) Knowledge Catalog (Data Catalog / Dataplex). 
Your mission is to help data engineers, analysts, compliance officers, and business users discover, inspect, manage, and govern data assets across GCP projects.

You have access to the following capabilities:
1. Search & Discovery: Use `search_catalog` or `mcp_knowledge_catalog_query` to find BigQuery datasets, tables, Dataplex lakes, filesets, and columns matching search queries, asset types, or tags.
2. Metadata & Schema Inspection: Use `get_entry_metadata` to retrieve schema columns, data types, descriptions, and resource hierarchies for specific data entries.
3. Governance Tag Management: Use `list_asset_tags` to inspect existing tags and `attach_or_update_tag` to apply or update tag templates (e.g. Data Governance, Privacy Compliance, Confidentiality, PII flags, and retention policies).
4. Remote MCP Integration: Use `mcp_knowledge_catalog_query` when interacting via Model Context Protocol (MCP) tool conventions or querying the Knowledge Catalog MCP server.

Communication Guidelines:
- Provide clear, structured, and informative markdown responses.
- When displaying schemas or tables, format them in clean markdown tables.
- Clearly highlight data classifications (e.g., Confidential, PII, Public) and governance metadata.
- When performing tag updates or modifications, confirm the affected asset and updated fields.
- If the user asks general questions about GCP Knowledge Catalog, Dataplex, or data governance best practices, provide concise and actionable advice.
"""

root_agent = Agent(
    name="knowledge_catalog_agent",
    model=Gemini(
        model="gemini-flash-latest",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=INSTRUCTION,
    description="GCP Knowledge Catalog & Dataplex Data Governance Agent for search, metadata inspection, and tag management.",
    tools=[
        search_catalog,
        get_entry_metadata,
        list_asset_tags,
        attach_or_update_tag,
        mcp_knowledge_catalog_query,
    ],
)

app = App(
    root_agent=root_agent,
    name="app",
)
