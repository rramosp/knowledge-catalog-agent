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

"""FastAPI application serving GCP Knowledge Catalog Agent, A2A routes, and local Web UI."""

import contextlib
import os
from collections.abc import AsyncIterator
from typing import Any, Dict, Optional

import google.auth
from a2a.server.tasks import InMemoryTaskStore
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from google.adk.cli.fast_api import get_fast_api_app
from google.adk.runners import Runner
from google.cloud import logging as google_cloud_logging
from google.genai import types
from pydantic import BaseModel

from app.app_utils import services
from app.app_utils.a2a import attach_a2a_routes
from app.app_utils.reasoning_engine_adapter import attach_reasoning_engine_routes
from app.app_utils.telemetry import setup_telemetry
from app.app_utils.typing import Feedback
from app.tools import (
    attach_or_update_tag,
    get_entry_metadata,
    list_asset_tags,
    mcp_knowledge_catalog_query,
    search_catalog,
)

load_dotenv()
setup_telemetry()
_, project_id = google.auth.default()
logging_client = google_cloud_logging.Client()
logger = logging_client.logger(__name__)
allow_origins = (
    os.getenv("ALLOW_ORIGINS", "").split(",") if os.getenv("ALLOW_ORIGINS") else None
)

AGENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    from app.agent import app as adk_app
    from app.agent import root_agent

    runner = Runner(
        app=adk_app,
        session_service=services.get_session_service(),
        artifact_service=services.get_artifact_service(),
        auto_create_session=True,
    )
    app.state.runner = runner
    app.state.agent_app_name = adk_app.name
    await attach_a2a_routes(
        app,
        agent=root_agent,
        runner=runner,
        task_store=InMemoryTaskStore(),
        rpc_path=f"/a2a/{adk_app.name}",
    )
    yield


app: FastAPI = get_fast_api_app(
    agents_dir=AGENT_DIR,
    web=True,
    artifact_service_uri=services.ARTIFACT_SERVICE_URI,
    allow_origins=allow_origins,
    session_service_uri=services.SESSION_SERVICE_URI,
    otel_to_cloud=False,
    lifespan=lifespan,
)
app.title = "knowledge-catalog"
app.description = "API and Web Interface for interacting with the GCP Knowledge Catalog Agent in Gemini Enterprise"
attach_reasoning_engine_routes(app)

# Mount static web assets
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
async def root():
    """Serves the local web interface for the GCP Knowledge Catalog Agent."""
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "GCP Knowledge Catalog Agent API is running."}


class ChatRequest(BaseModel):
    prompt: str
    session_id: Optional[str] = None


@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    """Executes a user prompt against the Gemini ADK Knowledge Catalog Agent."""
    runner: Runner = getattr(app.state, "runner", None)
    app_name = getattr(app.state, "agent_app_name", "app")

    if not runner:
        return JSONResponse(status_code=503, content={"error": "Agent runner is not initialized."})

    try:
        user_id = "local-web-user"
        session_id = request.session_id
        if not session_id:
            session = await runner.session_service.create_session(app_name=app_name, user_id=user_id)
            session_id = session.id

        content = types.Content(role="user", parts=[types.Part.from_text(text=request.prompt)])
        response_text = ""

        async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=content):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        response_text += part.text

        if not response_text:
            response_text = "I have processed your Knowledge Catalog request."

        return {
            "status": "success",
            "session_id": session_id,
            "response": response_text
        }
    except Exception as e:
        logger.log_struct({"error": str(e), "prompt": request.prompt}, severity="ERROR")
        return {
            "status": "error",
            "message": f"Error running agent: {str(e)}"
        }


@app.get("/api/catalog/search")
def search_catalog_endpoint(query: str = "", project_id: str = ""):
    """Search data assets across GCP projects."""
    return search_catalog(query=query, project_id=project_id)


@app.get("/api/catalog/entry")
def get_entry_endpoint(name: str):
    """Fetch metadata and schema for a specified Knowledge Catalog entry."""
    return get_entry_metadata(entry_name=name)


@app.get("/api/catalog/tags")
def list_tags_endpoint(name: str):
    """List attached governance tags for a data asset."""
    return list_asset_tags(entry_name=name)


class TagAttachRequest(BaseModel):
    entry_name: str
    tag_template_display_name: str
    tag_fields: Dict[str, Any]
    column: Optional[str] = ""


@app.post("/api/catalog/tags")
def attach_tag_endpoint(req: TagAttachRequest):
    """Attach or update a tag on a Knowledge Catalog asset."""
    return attach_or_update_tag(
        entry_name=req.entry_name,
        tag_template_display_name=req.tag_template_display_name,
        tag_fields=req.tag_fields,
        column=req.column or ""
    )


class McpRequest(BaseModel):
    tool_name: str
    parameters: Optional[Dict[str, Any]] = None


@app.post("/api/catalog/mcp")
def mcp_endpoint(req: McpRequest):
    """Invokes the Remote Knowledge Catalog MCP Server tool."""
    return mcp_knowledge_catalog_query(tool_name=req.tool_name, parameters=req.parameters or {})


@app.post("/feedback")
def collect_feedback(feedback: Feedback) -> dict[str, str]:
    """Collect and log feedback."""
    try:
        logger.log_struct(feedback.model_dump(), severity="INFO")
    except Exception:
        import logging
        logging.getLogger(__name__).info(f"Feedback received: {feedback.model_dump()}")
    return {"status": "success"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
