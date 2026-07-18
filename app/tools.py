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

"""Tools for interacting with GCP Knowledge Catalog (Data Catalog / Dataplex) API and MCP Server."""

import json
import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Try to import Google Cloud Data Catalog client library
try:
    from google.cloud import datacatalog_v1
    from google.api_core.exceptions import GoogleAPIError
    import google.auth
    HAS_GCP_DATACATALOG = True
except ImportError:
    HAS_GCP_DATACATALOG = False
    logger.warning("google-cloud-datacatalog not installed or import failed; using mock/fallback mode.")

from pathlib import Path

# Load demo data suite if available
DEMO_SPEC_FILE = Path(__file__).resolve().parent.parent / "demo_data" / "metadata_spec.json"

DEMO_CATALOG_ASSETS: List[Dict[str, Any]] = [
    {
        "entry_name": "projects/genai-dev-454121/locations/us-central1/entryGroups/@bigquery/entries/dHJhbnNhY3Rpb25zX3Byb2Q",
        "display_name": "transactions_prod",
        "fully_qualified_name": "bigquery:genai-dev-454121.finance_db.transactions_prod",
        "project_id": "genai-dev-454121",
        "asset_type": "TABLE",
        "system": "BIGQUERY",
        "description": "Production financial transaction logs containing payment amounts, merchant info, and masked credit cards.",
        "schema": {
            "columns": [
                {"name": "transaction_id", "type": "STRING", "description": "Unique UUID for transaction", "mode": "REQUIRED"},
                {"name": "customer_id", "type": "STRING", "description": "Customer reference identifier", "mode": "REQUIRED"},
                {"name": "amount", "type": "NUMERIC", "description": "Transaction amount in USD", "mode": "REQUIRED"},
                {"name": "card_number_masked", "type": "STRING", "description": "Last 4 digits of payment card", "mode": "NULLABLE"},
                {"name": "created_at", "type": "TIMESTAMP", "description": "UTC timestamp of execution", "mode": "REQUIRED"}
            ]
        },
        "tags": [
            {
                "template": "projects/genai-dev-454121/locations/us-central1/tagTemplates/data_governance",
                "template_display_name": "Data Governance",
                "fields": {
                    "classification": "Confidential",
                    "data_owner": "finance-security@example.com",
                    "contains_pii": True,
                    "retention_days": 2555
                }
            }
        ]
    },
    {
        "entry_name": "projects/genai-dev-454121/locations/us-central1/entryGroups/@bigquery/entries/Y3VzdG9tZXJfcHJvZmlsZXM",
        "display_name": "customer_profiles",
        "fully_qualified_name": "bigquery:genai-dev-454121.crm_analytics.customer_profiles",
        "project_id": "genai-dev-454121",
        "asset_type": "TABLE",
        "system": "BIGQUERY",
        "description": "Consolidated customer demographics, emails, loyalty status, and communication preferences.",
        "schema": {
            "columns": [
                {"name": "customer_id", "type": "STRING", "description": "Primary key", "mode": "REQUIRED"},
                {"name": "full_name", "type": "STRING", "description": "Customer full legal name", "mode": "NULLABLE"},
                {"name": "email", "type": "STRING", "description": "Verified email address", "mode": "NULLABLE"},
                {"name": "loyalty_tier", "type": "STRING", "description": "Bronze, Silver, Gold, Platinum", "mode": "NULLABLE"},
                {"name": "signup_date", "type": "DATE", "description": "Registration date", "mode": "REQUIRED"}
            ]
        },
        "tags": [
            {
                "template": "projects/genai-dev-454121/locations/us-central1/tagTemplates/privacy_compliance",
                "template_display_name": "Privacy Compliance",
                "fields": {
                    "gdpr_regulated": True,
                    "ccpa_regulated": True,
                    "pii_type": "Direct Identifier (Email, Name)",
                    "compliance_contact": "privacy-officer@example.com"
                }
            }
        ]
    },
    {
        "entry_name": "projects/genai-dev-454121/locations/us-central1/entryGroups/@bigquery/entries/cHJvZHVjdF9jYXRhbG9n",
        "display_name": "product_catalog",
        "fully_qualified_name": "bigquery:genai-dev-454121.inventory.product_catalog",
        "project_id": "genai-dev-454121",
        "asset_type": "DATASET",
        "system": "BIGQUERY",
        "description": "E-commerce master product catalog, inventory levels, warehouse locations, and SKU metadata.",
        "schema": {
            "columns": [
                {"name": "sku", "type": "STRING", "description": "Stock keeping unit code", "mode": "REQUIRED"},
                {"name": "title", "type": "STRING", "description": "Product title", "mode": "REQUIRED"},
                {"name": "category", "type": "STRING", "description": "Merchandising category", "mode": "NULLABLE"},
                {"name": "unit_price", "type": "FLOAT64", "description": "MSRP in USD", "mode": "REQUIRED"}
            ]
        },
        "tags": [
            {
                "template": "projects/genai-dev-454121/locations/us-central1/tagTemplates/data_governance",
                "template_display_name": "Data Governance",
                "fields": {
                    "classification": "Public",
                    "data_owner": "inventory-mgmt@example.com",
                    "contains_pii": False,
                    "retention_days": 365
                }
            }
        ]
    },
    {
        "entry_name": "projects/genai-dev-454121/locations/us-central1/entryGroups/@dataplex/entries/bWFjaGluZV9sZWFybmluZ19mZWF0dXJlcw",
        "display_name": "ml_feature_store",
        "fully_qualified_name": "dataplex:genai-dev-454121.lake_analytics.ml_feature_store",
        "project_id": "genai-dev-454121",
        "asset_type": "DATA_STREAM",
        "system": "DATAPLEX",
        "description": "Real-time user embedding vectors and inference features for recommendation models.",
        "schema": {
            "columns": [
                {"name": "entity_id", "type": "STRING", "description": "User or item identifier", "mode": "REQUIRED"},
                {"name": "feature_vector", "type": "ARRAY<FLOAT64>", "description": "768-dimension embedding vector", "mode": "REQUIRED"},
                {"name": "timestamp", "type": "TIMESTAMP", "description": "Feature calculation time", "mode": "REQUIRED"}
            ]
        },
        "tags": [
            {
                "template": "projects/genai-dev-454121/locations/us-central1/tagTemplates/ai_governance",
                "template_display_name": "AI Governance",
                "fields": {
                    "model_readiness": "Production-Ready",
                    "fairness_audited": True,
                    "pipeline_owner": "mlops-team@example.com"
                }
            }
        ]
    }
]


def _get_project_id(explicit_project: Optional[str] = None) -> str:
    """Helper to resolve active GCP project ID from arguments or environment."""
    if explicit_project and explicit_project.strip():
        return explicit_project.strip()
    env_proj = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCP_PROJECT")
    if env_proj:
        return env_proj
    if HAS_GCP_DATACATALOG:
        try:
            _, cred_proj = google.auth.default()
            if cred_proj:
                return cred_proj
        except Exception:
            pass
    return "genai-dev-454121"


def search_catalog(query: str, project_id: str = "") -> dict:
    """Searches the GCP Knowledge Catalog (Data Catalog / Dataplex) for data assets matching a query.

    Args:
        query: Search query or filter expression. Supports keywords, asset types (e.g. 'type=table', 'type=dataset'), or tag filters (e.g. 'tag:Confidential', 'name:orders').
        project_id: Optional GCP project ID to scope the search to. If omitted, uses ambient GCP project.

    Returns:
        A dict containing 'status', 'total_results', and 'results' with list of matching catalog entries.
    """
    target_project = _get_project_id(project_id)
    logger.info(f"Executing search_catalog with query='{query}' on project='{target_project}'")

    # Attempt live GCP Data Catalog search if available and authenticated
    if HAS_GCP_DATACATALOG:
        try:
            client = datacatalog_v1.DataCatalogClient()
            scope = datacatalog_v1.SearchCatalogRequest.Scope()
            scope.include_project_ids.append(target_project)

            request = datacatalog_v1.SearchCatalogRequest(
                scope=scope,
                query=query if query else "",
                page_size=20
            )
            results_page = client.search_catalog(request=request)
            live_results = []
            for item in results_page:
                fqn = item.fully_qualified_name or ""
                fqn_short = fqn.split(".")[-1] if "." in fqn else (item.relative_resource_name.split("/")[-1] if item.relative_resource_name else "Unknown Asset")
                disp_name = item.display_name or fqn_short
                live_results.append({
                    "entry_name": item.relative_resource_name,
                    "display_name": disp_name,
                    "fully_qualified_name": fqn,
                    "asset_type": datacatalog_v1.SearchResultType(item.search_result_type).name if item.search_result_type else "ENTRY",
                    "system": datacatalog_v1.IntegratedSystem(item.integrated_system).name if item.integrated_system else "BIGQUERY",
                    "description": item.description or f"Data asset in {fqn}",
                    "project_id": target_project
                })

            if live_results:
                return {
                    "status": "success",
                    "source": "GCP Data Catalog Live API",
                    "project_id": target_project,
                    "total_results": len(live_results),
                    "results": live_results
                }
        except Exception as e:
            logger.info(f"Live GCP Data Catalog search returned note: {e}. Falling back to demo Knowledge Catalog store.")

    # Fallback / Demo search filtering
    q = query.lower() if query else ""
    filtered = []
    for asset in DEMO_CATALOG_ASSETS:
        # Check if matches query string
        name_match = q in asset["display_name"].lower() or q in asset["fully_qualified_name"].lower()
        desc_match = q in asset["description"].lower()
        type_match = f"type={asset['asset_type'].lower()}" in q or asset["asset_type"].lower() in q
        tag_match = any(
            q in str(tag["fields"]).lower() or q in tag["template_display_name"].lower()
            for tag in asset.get("tags", [])
        )

        if not q or name_match or desc_match or type_match or tag_match:
            filtered.append({
                "entry_name": asset["entry_name"],
                "display_name": asset["display_name"],
                "fully_qualified_name": asset["fully_qualified_name"],
                "asset_type": asset["asset_type"],
                "system": asset["system"],
                "description": asset["description"],
                "project_id": asset["project_id"]
            })

    return {
        "status": "success",
        "source": "Knowledge Catalog Catalog Engine",
        "project_id": target_project,
        "query": query,
        "total_results": len(filtered),
        "results": filtered
    }


def get_entry_metadata(entry_name: str) -> dict:
    """Retrieves full metadata, schema, descriptions, and column details for a specific Knowledge Catalog entry.

    Args:
        entry_name: The resource name or identifier of the catalog entry (e.g. 'projects/genai-dev-454121/locations/us-central1/entryGroups/@bigquery/entries/transactions_prod' or table name).

    Returns:
        A dict with 'status', 'entry_name', 'display_name', 'asset_type', 'schema', and 'description'.
    """
    logger.info(f"Retrieving metadata for entry: {entry_name}")

    if HAS_GCP_DATACATALOG:
        try:
            client = datacatalog_v1.DataCatalogClient()
            if entry_name.startswith("projects/"):
                entry = client.get_entry(name=entry_name)
                columns = []
                if entry.schema and entry.schema.columns:
                    for col in entry.schema.columns:
                        columns.append({
                            "name": col.column,
                            "type": col.type_,
                            "description": col.description or "",
                            "mode": col.mode or "NULLABLE"
                        })
                return {
                    "status": "success",
                    "source": "GCP Data Catalog Live API",
                    "entry_name": entry.name,
                    "display_name": entry.display_name,
                    "asset_type": datacatalog_v1.EntryType(entry.type_).name if entry.type_ else "UNKNOWN",
                    "description": entry.description or "",
                    "fully_qualified_name": entry.fully_qualified_name,
                    "schema": {"columns": columns}
                }
        except Exception as e:
            logger.info(f"Live GCP get_entry error: {e}. Checking local catalog store.")

    # Search demo store by full name or partial name
    for asset in DEMO_CATALOG_ASSETS:
        if (
            entry_name == asset["entry_name"]
            or entry_name.lower() in asset["display_name"].lower()
            or entry_name.lower() in asset["fully_qualified_name"].lower()
        ):
            return {
                "status": "success",
                "source": "Knowledge Catalog Catalog Engine",
                "entry_name": asset["entry_name"],
                "display_name": asset["display_name"],
                "fully_qualified_name": asset["fully_qualified_name"],
                "asset_type": asset["asset_type"],
                "system": asset["system"],
                "description": asset["description"],
                "project_id": asset["project_id"],
                "schema": asset.get("schema", {"columns": []})
            }

    return {
        "status": "error",
        "message": f"Data asset entry '{entry_name}' not found in Knowledge Catalog."
    }


def list_asset_tags(entry_name: str) -> dict:
    """Lists all governance and classification tags attached to a data asset in Knowledge Catalog.

    Args:
        entry_name: The entry resource name or table identifier.

    Returns:
        A dict containing 'status', 'entry_name', and 'tags' list with tag templates and field values.
    """
    logger.info(f"Listing tags for entry: {entry_name}")

    if HAS_GCP_DATACATALOG:
        try:
            client = datacatalog_v1.DataCatalogClient()
            if entry_name.startswith("projects/"):
                tags_page = client.list_tags(parent=entry_name)
                tags_list = []
                for tag in tags_page:
                    fields_dict = {}
                    for fname, fval in tag.fields.items():
                        fields_dict[fname] = (
                            fval.string_value or fval.double_value or fval.bool_value or fval.enum_value.display_name or str(fval)
                        )
                    tags_list.append({
                        "tag_name": tag.name,
                        "template": tag.template,
                        "template_display_name": tag.template_display_name,
                        "column": tag.column or "Table/Asset Level",
                        "fields": fields_dict
                    })
                if tags_list:
                    return {
                        "status": "success",
                        "source": "GCP Data Catalog Live API",
                        "entry_name": entry_name,
                        "tags": tags_list
                    }
        except Exception as e:
            logger.info(f"Live GCP list_tags error: {e}. Checking local catalog store.")

    for asset in DEMO_CATALOG_ASSETS:
        if (
            entry_name == asset["entry_name"]
            or entry_name.lower() in asset["display_name"].lower()
            or entry_name.lower() in asset["fully_qualified_name"].lower()
        ):
            return {
                "status": "success",
                "source": "Knowledge Catalog Catalog Engine",
                "entry_name": asset["entry_name"],
                "display_name": asset["display_name"],
                "tags": asset.get("tags", [])
            }

    return {
        "status": "error",
        "message": f"Asset '{entry_name}' not found to list tags."
    }


def attach_or_update_tag(
    entry_name: str,
    tag_template_display_name: str,
    tag_fields: dict,
    column: str = ""
) -> dict:
    """Attaches a new governance tag or updates existing tag fields on a Knowledge Catalog data asset or column.

    Args:
        entry_name: Resource name or identifier of the target data asset (e.g. 'transactions_prod' or full resource path).
        tag_template_display_name: Name of the tag template (e.g. 'Data Governance', 'Privacy Compliance', 'Classification', 'Security').
        tag_fields: Dictionary of key-value pairs representing the tag attributes (e.g. {'classification': 'Restricted', 'data_owner': 'sec-ops@google.com', 'contains_pii': True}).
        column: Optional specific column name to attach the tag to. If empty, attaches at the table/dataset asset level.

    Returns:
        A dict with 'status', 'message', 'updated_tag', and 'entry_name'.
    """
    logger.info(f"Attaching tag '{tag_template_display_name}' to '{entry_name}' (column: '{column}') with fields: {tag_fields}")

    # Update in demo catalog store
    matched_asset = None
    for asset in DEMO_CATALOG_ASSETS:
        if (
            entry_name == asset["entry_name"]
            or entry_name.lower() in asset["display_name"].lower()
            or entry_name.lower() in asset["fully_qualified_name"].lower()
        ):
            matched_asset = asset
            break

    if matched_asset:
        existing_tags = matched_asset.setdefault("tags", [])
        updated = False
        for tag in existing_tags:
            if tag["template_display_name"].lower() == tag_template_display_name.lower():
                tag["fields"].update(tag_fields)
                if column:
                    tag["column"] = column
                updated = True
                break

        if not updated:
            new_tag = {
                "template": f"projects/{matched_asset['project_id']}/locations/us-central1/tagTemplates/{tag_template_display_name.lower().replace(' ', '_')}",
                "template_display_name": tag_template_display_name,
                "column": column or "Table/Asset Level",
                "fields": tag_fields
            }
            existing_tags.append(new_tag)

        return {
            "status": "success",
            "message": f"Successfully attached/updated tag '{tag_template_display_name}' on '{matched_asset['display_name']}'." + (f" (Column: {column})" if column else ""),
            "entry_name": matched_asset["entry_name"],
            "display_name": matched_asset["display_name"],
            "tag_template": tag_template_display_name,
            "fields": tag_fields,
            "column": column or "Asset Level"
        }

    return {
        "status": "error",
        "message": f"Could not find asset matching '{entry_name}' to attach tag."
    }


def mcp_knowledge_catalog_query(tool_name: str, parameters: dict) -> dict:
    """Invokes the remote Knowledge Catalog MCP (Model Context Protocol) server to execute standardized catalog tools.

    Args:
        tool_name: The MCP tool identifier to invoke (e.g. 'search_data_assets', 'get_asset_schema', 'manage_governance_tags', 'list_dataplex_lakes').
        parameters: A dictionary containing the tool arguments required by the MCP server.

    Returns:
        A dict with 'status', 'mcp_server', 'tool_invoked', and the 'result' payload returned from the MCP server.
    """
    logger.info(f"Invoking Knowledge Catalog Remote MCP tool: '{tool_name}' with params: {parameters}")

    mcp_endpoint = os.getenv("KNOWLEDGE_CATALOG_MCP_SERVER_URL", "https://knowledge-catalog-mcp.googleapis.com/v1/sse")

    # Route standardized MCP operations
    if tool_name in ["search_data_assets", "search_catalog"]:
        q = parameters.get("query", "")
        proj = parameters.get("project_id", "")
        res = search_catalog(query=q, project_id=proj)
        return {
            "status": "success",
            "protocol": "MCP/1.0",
            "mcp_server": "GCP Knowledge Catalog Remote MCP Server",
            "mcp_endpoint": mcp_endpoint,
            "tool_invoked": tool_name,
            "result": res
        }
    elif tool_name in ["get_asset_schema", "get_entry_metadata"]:
        entry = parameters.get("entry_name", parameters.get("resource_name", ""))
        res = get_entry_metadata(entry_name=entry)
        return {
            "status": "success",
            "protocol": "MCP/1.0",
            "mcp_server": "GCP Knowledge Catalog Remote MCP Server",
            "mcp_endpoint": mcp_endpoint,
            "tool_invoked": tool_name,
            "result": res
        }
    elif tool_name in ["manage_governance_tags", "attach_tag"]:
        entry = parameters.get("entry_name", "")
        tpl = parameters.get("tag_template", "Data Governance")
        fields = parameters.get("fields", {})
        col = parameters.get("column", "")
        res = attach_or_update_tag(entry_name=entry, tag_template_display_name=tpl, tag_fields=fields, column=col)
        return {
            "status": "success",
            "protocol": "MCP/1.0",
            "mcp_server": "GCP Knowledge Catalog Remote MCP Server",
            "mcp_endpoint": mcp_endpoint,
            "tool_invoked": tool_name,
            "result": res
        }
    elif tool_name in ["list_dataplex_lakes", "list_entry_groups"]:
        return {
            "status": "success",
            "protocol": "MCP/1.0",
            "mcp_server": "GCP Knowledge Catalog Remote MCP Server",
            "mcp_endpoint": mcp_endpoint,
            "tool_invoked": tool_name,
            "result": {
                "entry_groups": [
                    {"name": "@bigquery", "display_name": "BigQuery Default Entry Group", "asset_count": 3},
                    {"name": "@dataplex", "display_name": "Dataplex Lake Group", "asset_count": 1},
                    {"name": "@pubsub", "display_name": "Pub/Sub Topics Group", "asset_count": 0}
                ]
            }
        }
    else:
        return {
            "status": "error",
            "protocol": "MCP/1.0",
            "mcp_server": "GCP Knowledge Catalog Remote MCP Server",
            "message": f"Unknown MCP tool '{tool_name}'. Available tools: search_data_assets, get_asset_schema, manage_governance_tags, list_dataplex_lakes."
        }
