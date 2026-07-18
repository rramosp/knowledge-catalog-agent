# GCP Knowledge Catalog Agent and Demo

Agent generated with `agents-cli` version `1.0.0`

## Project Structure

```
knowledge-catalog/
├── app/         # Core agent code
│   ├── agent.py               # Main agent logic
│   ├── fast_api_app.py        # FastAPI Backend server
│   └── app_utils/             # App utilities and helpers
├── tests/                     # Unit, integration, and load tests
├── GEMINI.md                  # AI-assisted development guide
└── pyproject.toml             # Project dependencies
```

> 💡 **Tip:** Use [Antigravity CLI](https://antigravity.google/) for AI-assisted development - project context is pre-configured in `GEMINI.md`.

## Requirements

Before you begin, ensure you have:
- **uv**: Python package manager (used for all dependency management in this project) - [Install](https://docs.astral.sh/uv/getting-started/installation/) ([add packages](https://docs.astral.sh/uv/concepts/dependencies/) with `uv add <package>`)
- **agents-cli**: Agents CLI - Install with `uv tool install google-agents-cli`
- **Google Cloud SDK**: For GCP services - [Install](https://cloud.google.com/sdk/docs/install)


## Quick Start

Install `agents-cli` and its skills if not already installed:

```bash
uvx google-agents-cli setup
```

Install required packages:

```bash
agents-cli install
```

Test the agent with a local web server:

```bash
agents-cli playground
```

You can also use features from the [ADK](https://adk.dev/) CLI with `uv run adk`.

## Commands

| Command              | Description                                                                                 |
| -------------------- | ------------------------------------------------------------------------------------------- |
| `agents-cli install` | Install dependencies using uv                                                         |
| `agents-cli playground` | Launch local development environment                                                  |
| `agents-cli lint`    | Run code quality checks                                                               |
| `agents-cli eval`    | Evaluate agent behavior (generate, grade, analyze, and more — see `agents-cli eval --help`) |
| `uv run pytest tests/unit tests/integration` | Run unit and integration tests                                                        || [A2A Inspector](https://github.com/a2aproject/a2a-inspector) | Launch A2A Protocol Inspector                                                        |

## 🛠️ Project Management

| Command | What It Does |
|---------|--------------|
| `agents-cli scaffold enhance` | Add CI/CD pipelines and Terraform infrastructure |
| `agents-cli infra cicd` | One-command setup of entire CI/CD pipeline + infrastructure |
| `agents-cli scaffold upgrade` | Auto-upgrade to latest version while preserving customizations |

---

## Development

Edit your agent logic in `app/agent.py` and test with `agents-cli playground` - it auto-reloads on save.

## 📊 Demo Data Suite & GCP Ingestion

This project includes a turnkey **Demo Data Suite** with sample assets across **BigQuery/Bigtable**, **Cloud Storage (GCS)**, **Vertex AI / Dataplex**, and **Data Catalog Tag Templates** to easily demonstrate and test the agent in any GCP project.

### 📁 Demo Suite Contents (`demo_data/`)
* **BigQuery / Bigtable**:
  - `financial_transactions.json` (`finance_db.transactions_prod`): Transaction logs with payment amounts and masked credit cards.
  - `customer_profiles.json` (`crm_analytics.customer_profiles`): Customer PII datasets with emails, loyalty tiers, and phone numbers.
  - `product_catalog.json` (`inventory.product_catalog`): E-commerce product catalog with SKUs and unit prices.
* **Cloud Storage (GCS)**:
  - `customer_feedback_transcripts.txt`: Unstructured transcripts and data discovery logs.
  - `governance_policy.txt`: Corporate Data Governance & Privacy Compliance Policy documentation.
* **Vertex AI & Dataplex**:
  - `ml_feature_store`: Dataplex data stream / Vertex AI ML feature store embeddings.
* **Data Catalog Tag Templates**:
  - `Data Governance`: Fields for `classification` (Confidential/Public), `data_owner`, `contains_pii`, and `retention_days`.
  - `Privacy Compliance`: Fields for `gdpr_regulated`, `ccpa_regulated`, `pii_type`, and `compliance_contact`.
  - `AI Governance`: Fields for `model_readiness`, `fairness_audited`, and `pipeline_owner`.

---

### ⚡ Running the Ingestion Script

Run the automated ingestion script to provision datasets, upload files to Cloud Storage, and register Data Catalog tag templates in your target GCP project:

```bash
# 1. Ingest demo data into your target GCP project (e.g. us-central1)
uv run python scripts/ingest_demo_data.py --project-id <your-gcp-project> --location us-central1

# 2. Or run in Dry-Run / Local Seed mode (for offline demos and testing)
uv run python scripts/ingest_demo_data.py --dry-run
```

Once ingested, all demo assets are immediately ready for queries, metadata inspection, and tag attachments via the Knowledge Catalog Agent in both the local web interface and Gemini Enterprise.

---

### 🔎 Verifying Ingested Data in Google Cloud Console

After running the ingestion script, you can verify the provisioned demo resources directly in the [Google Cloud Console](https://console.cloud.google.com/):

1. **BigQuery Studio** (`Navigation Menu > BigQuery > BigQuery Studio`):
   * Expand your project ID in the left **Explorer** panel.
   * Verify the 3 demo datasets and query the sample rows:
     * `finance_db.transactions_prod`
     * `crm_analytics.customer_profiles`
     * `inventory.product_catalog`

2. **Cloud Storage** (`Navigation Menu > Cloud Storage > Buckets`):
   * Open bucket `gs://<your-gcp-project>-knowledge-catalog-demo-docs`.
   * Verify the uploaded policy documents: `customer_feedback_transcripts.txt` and `governance_policy.txt`.

3. **Dataplex / Knowledge Catalog** (`Navigation Menu > Dataplex > Search / Manage`):
   * **Search & Discovery**: Search for `transactions_prod` or `customer_profiles` to view indexed schema types, column descriptions, and resource hierarchies.
   * **Tag Templates**: Navigate to **Data Catalog > Tag Templates** (or Dataplex Aspect Types) to verify `Data Governance`, `Privacy Compliance`, and `AI Governance`.

## Deployment

The GCP Knowledge Catalog Agent is designed for containerized deployment to **Vertex AI Agent Runtime** (Agent Platform) or **Cloud Run / GKE**, and direct registration with **Gemini Enterprise**.

### 📍 Where the Agent is Deployed
1. **Vertex AI Agent Runtime (Primary Target)**: Managed, scalable container environment on Google Cloud. It automatically builds the Docker container and wires up Vertex AI Sessions, ambient GCP credentials, and the `:streamQuery` ADK contract.
2. **Gemini Enterprise App**: Once deployed, the agent is published and registered in the Gemini Enterprise App ecosystem so business users, compliance officers, and data engineers can select and interact with the agent directly from the **Gemini Chat UI**.
3. **Cloud Run / GKE (Alternative Target)**: Standalone container deployment exposing the FastAPI web interface and standard A2A (Agent-to-Agent) protocol endpoints.

---

### 🚀 How to Deploy

1. **Configure GCP Project & Deployment Target**:
   ```bash
   gcloud config set project <your-project-id>
   agents-cli scaffold enhance . --deployment-target agent_runtime
   ```

2. **Deploy to Google Cloud**:
   ```bash
   agents-cli deploy --no-confirm-project
   ```
   *(Note: Deployments typically take 5–10 minutes. You can run `agents-cli deploy --no-wait` followed by `agents-cli deploy --status` to monitor progress.)*

3. **Publish / Register with Gemini Enterprise**:
   ```bash
   agents-cli publish gemini-enterprise \
     --gemini-enterprise-app-id projects/<PROJECT_NUMBER>/locations/global/collections/default_collection/engines/<APP_ID> \
     --display-name "GCP Knowledge Catalog Agent" \
     --description "AI Agent for discovering GCP datasets, inspecting metadata, and managing governance tags."
   ```

---

### ✅ How to Verify Deployment is Correct

1. **Check Deployment Status via CLI**:
   ```bash
   agents-cli deploy --status
   ```
2. **Inspect Google Cloud Logging**:
   Verify runtime initialization and streaming queries in Cloud Logging:
   ```bash
   gcloud logging read "resource.type=aiplatform.googleapis.com/ReasoningEngine" --limit=20
   ```
3. **Verify Agent Registry Listing**:
   Check that the agent is registered in the Google Cloud Agent Registry fleet:
   ```bash
   gcloud alpha agent-registry agents list --project=<your-project-id>
   ```
4. **Smoke Test the Live Deployed Agent**:
   Run a test prompt against the deployed service URL or reasoning engine:
   ```bash
   agents-cli run --url <deployed-service-url> --mode adk "Search for BigQuery tables in Knowledge Catalog"
   ```

---

### 💬 How to Interact with the Deployed Agent

1. **In Gemini Enterprise Chat UI**:
   * Open the **Gemini Enterprise Web App** in your browser.
   * In the chat interface, click the **Agent Picker** dropdown and select **GCP Knowledge Catalog Agent**.
   * Ask natural language questions (e.g., *"Find all customer PII tables in project analytics-prod"* or *"Attach the Confidential governance tag to orders_db"*).

2. **Via Local & Deployed Web Interface**:
   * Access the interactive web portal at `http://localhost:8000` (or your deployed Cloud Run URL).
   * Use the **Live Agent Chat**, **Asset Explorer**, **Schema Inspector**, **Tag Management Studio**, and **Remote MCP Hub** tabs.

3. **Via Agent-to-Agent (A2A) Protocol**:
   * Other autonomous agents can invoke this agent via the standard A2A JSON-RPC protocol endpoint at `/a2a/app/` using the well-known agent card at `/a2a/app/.well-known/agent-card.json`.

## Example Queries

Below is a curated suite of 20 example prompts demonstrating the agent's capabilities across GCP Knowledge Catalog functionalities (Search, Metadata Inspection, Governance Tagging, and MCP Server queries) and GCP services (BigQuery, Cloud Storage, Vertex AI, Dataplex, and Data Catalog Tag Templates).

### 🔍 1. Asset Discovery & Search
1. **BigQuery Table Discovery**: `"Search Knowledge Catalog for all production financial tables in dataset finance_db."`
2. **PII Asset Identification**: `"Find all datasets and tables across GCP projects that contain customer PII or email addresses."`
3. **Cross-Service Search**: `"List all BigQuery tables, Dataplex lakes, and Cloud Storage filesets indexed in Knowledge Catalog."`
4. **Tag-Based Filtering**: `"Search for all data assets tagged with classification=Confidential."`
5. **Dataplex Stream Lookup**: `"Discover any Dataplex streams or feature store assets in the machine learning zone."`

### 📋 2. Schema Inspection & Metadata Analysis
6. **Column Schema Explorer**: `"Show the full schema, data types, and column descriptions for the transactions_prod table."`
7. **Customer Demographics Inspection**: `"What columns and data modes are available in the crm_analytics.customer_profiles table?"`
8. **Catalog Hierarchy Check**: `"What is the fully qualified resource name and integrated system for the product_catalog dataset?"`
9. **Unstructured Asset Metadata**: `"Show the metadata and storage location for customer feedback transcripts in Cloud Storage."`
10. **Vertex AI Feature Store Inspection**: `"Inspect the schema and embedding dimensions for the ml_feature_store asset."`

### 🏷️ 3. Governance Tag Management & Compliance
11. **View Active Governance Tags**: `"List all attached Data Catalog tags and classification fields on the customer_profiles table."`
12. **Attach Confidentiality Tag**: `"Attach the 'Data Governance' tag template to table transactions_prod with classification='Confidential' and data_owner='sec-team@google.com'."`
13. **Apply GDPR & Privacy Compliance**: `"Update the 'Privacy Compliance' tag on crm_analytics.customer_profiles to set gdpr_regulated=true and pii_type='Direct Identifier'."`
14. **Column-Level Tagging**: `"Attach the 'Privacy Compliance' tag specifically to the email column in customer_profiles."`
15. **AI Governance Certification**: `"Attach the 'AI Governance' tag to ml_feature_store with model_readiness='Production-Ready' and fairness_audited=true."`
16. **Retention Policy Update**: `"Set the retention_days field to 2555 (7 years) on the financial_transactions data asset."`

### ⚡ 4. Remote MCP Server Queries
17. **Discover Entry Groups via MCP**: `"Use the Knowledge Catalog MCP server to query all active entry groups (@bigquery, @dataplex, @pubsub)."`
18. **MCP Asset Schema Invocation**: `"Invoke the get_asset_schema MCP tool for the product_catalog table."`
19. **Automated MCP Tagging**: `"Execute the manage_governance_tags MCP tool to apply the Data Governance template to inventory.product_catalog."`
20. **Full MCP Governance Audit**: `"Run a Knowledge Catalog MCP query to audit all compliance-tagged assets in project genai-dev-454121."`

## Observability

Built-in telemetry exports to Cloud Trace, BigQuery, and Cloud Logging.

## A2A Inspector

This agent supports the [A2A Protocol](https://a2a-protocol.org/). Use the [A2A Inspector](https://github.com/a2aproject/a2a-inspector) to test interoperability.
See the [A2A Inspector docs](https://github.com/a2aproject/a2a-inspector) for details.
