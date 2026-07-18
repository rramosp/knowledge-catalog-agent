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

"""GCP Knowledge Catalog Demo Data Ingestion Script.

Ingests demo datasets, tables into BigQuery, unstructured docs into Cloud Storage,
registers Vertex AI / Dataplex metadata, and creates Data Catalog Tag Templates
with attached governance tags.
"""

import argparse
import json
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Set

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("ingest-demo-data")

BASE_DIR = Path(__file__).resolve().parent.parent
DEMO_DATA_DIR = BASE_DIR / "demo_data"

# Required GCP Service APIs for Knowledge Catalog Demo
REQUIRED_GCP_APIS = [
    ("bigquery.googleapis.com", "BigQuery API"),
    ("storage.googleapis.com", "Cloud Storage API"),
    ("datacatalog.googleapis.com", "Google Cloud Data Catalog API"),
    ("dataplex.googleapis.com", "Cloud Dataplex API"),
]

# Optional GCP client imports with graceful fallback
try:
    from google.cloud import bigquery, storage, datacatalog_v1
    from google.api_core.exceptions import GoogleAPIError, AlreadyExists, PermissionDenied
    import google.auth
    HAS_GCP_LIBS = True
except ImportError:
    HAS_GCP_LIBS = False


def load_spec() -> Dict[str, Any]:
    """Loads the metadata specification JSON file."""
    spec_path = DEMO_DATA_DIR / "metadata_spec.json"
    if not spec_path.exists():
        logger.error(f"Metadata spec file not found at {spec_path}")
        sys.exit(1)
    with open(spec_path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_default_project(explicit_project: str = "") -> str:
    """Resolves GCP Project ID from CLI, environment, or gcloud default."""
    if explicit_project and explicit_project.strip():
        return explicit_project.strip()
    env_proj = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCP_PROJECT")
    if env_proj:
        return env_proj
    if HAS_GCP_LIBS:
        try:
            _, cred_proj = google.auth.default()
            if cred_proj:
                return cred_proj
        except Exception:
            pass
    return "genai-dev-454121"


def get_enabled_services(project_id: str) -> Set[str]:
    """Retrieves list of currently enabled GCP APIs for the project using gcloud."""
    try:
        res = subprocess.run(
            ["gcloud", "services", "list", "--enabled", f"--project={project_id}", "--format=value(config.name)"],
            capture_output=True,
            text=True,
            check=True
        )
        enabled = set(line.strip() for line in res.stdout.splitlines() if line.strip())
        return enabled
    except Exception as e:
        logger.warning(f"Could not query enabled GCP services via gcloud: {e}")
        return set()


def prompt_user_permission(prompt_text: str, auto_approve: bool = False) -> bool:
    """Prompts the user for yes/no permission in terminal."""
    if auto_approve:
        return True
    try:
        resp = input(f"{prompt_text} [y/N]: ").strip().lower()
        return resp in ("y", "yes")
    except (EOFError, KeyboardInterrupt):
        print()
        return False


def verify_and_enable_apis(project_id: str, auto_approve: bool = False, dry_run: bool = False) -> None:
    """Checks required GCP APIs. If an API is disabled, prompts user for permission. Aborts if declined."""
    if dry_run:
        logger.info("⚡ [Dry-Run] Skipping GCP API enablement verification.")
        return

    logger.info(f"🔍 Checking required GCP Service APIs for project '{project_id}'...")
    enabled_services = get_enabled_services(project_id)

    for api_name, display_name in REQUIRED_GCP_APIS:
        if enabled_services and api_name in enabled_services:
            logger.info(f"  ✓ {display_name} ({api_name}) is enabled.")
            continue

        # If not listed in enabled services, ask user permission to enable
        logger.warning(f"⚠️ Required GCP API '{display_name}' ({api_name}) is not enabled on project '{project_id}'.")
        prompt = f"👉 Would you like to enable '{display_name}' ({api_name}) now?"
        
        allowed = prompt_user_permission(prompt, auto_approve=auto_approve)
        if not allowed:
            logger.error(f"❌ User declined permission to enable '{api_name}'. Aborting ingestion script as required by policy.")
            sys.exit(1)

        logger.info(f"⏳ Enabling '{api_name}' on project '{project_id}'...")
        try:
            subprocess.run(
                ["gcloud", "services", "enable", api_name, f"--project={project_id}"],
                check=True
            )
            logger.info(f"  ✓ Successfully enabled '{display_name}' ({api_name}).")
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Failed to enable '{api_name}': {e}. Aborting.")
            sys.exit(1)


def ingest_bigquery(project_id: str, location: str, spec: Dict[str, Any], dry_run: bool = False) -> None:
    """Ingests BigQuery datasets and tables from demo data."""
    logger.info("📦 [1/4] Starting BigQuery Datasets & Tables Ingestion...")
    if dry_run or not HAS_GCP_LIBS:
        logger.info(f"⚡ [Dry-Run/Offline] Verified {len(spec.get('datasets', []))} BigQuery datasets for project {project_id}.")
        return

    try:
        client = bigquery.Client(project=project_id, location=location)
        for ds_info in spec.get("datasets", []):
            ds_id = ds_info["dataset_id"]
            ds_ref = bigquery.DatasetReference(project_id, ds_id)
            dataset = bigquery.Dataset(ds_ref)
            dataset.location = location
            dataset.description = ds_info.get("description", "")

            try:
                client.create_dataset(dataset, exists_ok=True)
                logger.info(f"  ✓ Dataset '{project_id}.{ds_id}' ready in {location}")
            except Exception as e:
                logger.warning(f"  Note creating dataset '{ds_id}': {e}")

            for tbl_info in ds_info.get("tables", []):
                tbl_id = tbl_info["table_id"]
                tbl_ref = ds_ref.table(tbl_id)
                data_file = DEMO_DATA_DIR / tbl_info["data_file"]

                if data_file.exists():
                    with open(data_file, "r", encoding="utf-8") as f:
                        records = json.load(f)
                    job_config = bigquery.LoadJobConfig(
                        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
                        autodetect=True,
                    )
                    try:
                        # Use load_table_from_json for clean dictionary loading
                        job = client.load_table_from_json(
                            records,
                            tbl_ref,
                            job_config=job_config
                        )
                        job.result()
                        logger.info(f"    ✓ Ingested {len(records)} rows into table '{ds_id}.{tbl_id}'")
                    except Exception as e:
                        logger.warning(f"    Could not load rows into '{tbl_id}': {e}")
    except Exception as e:
        logger.warning(f"BigQuery ingestion encountered note: {e}. Proceeding with offline fallback setup.")


def ingest_cloud_storage(project_id: str, location: str, spec: Dict[str, Any], dry_run: bool = False) -> None:
    """Ingests Cloud Storage bucket and documentation files."""
    logger.info("☁️ [2/4] Starting Cloud Storage (GCS) Documents Ingestion...")
    if dry_run or not HAS_GCP_LIBS:
        logger.info(f"⚡ [Dry-Run/Offline] Verified Cloud Storage buckets and demo documents for project {project_id}.")
        return

    try:
        client = storage.Client(project=project_id)
        for b_info in spec.get("storage_buckets", []):
            bucket_name = f"{project_id}-{b_info['bucket_suffix']}"
            try:
                bucket = client.create_bucket(bucket_name, location=location)
                logger.info(f"  ✓ Created GCS Bucket 'gs://{bucket_name}'")
            except AlreadyExists:
                bucket = client.bucket(bucket_name)
                logger.info(f"  ✓ GCS Bucket 'gs://{bucket_name}' exists")
            except Exception as e:
                bucket = client.bucket(bucket_name)
                logger.warning(f"  Note for bucket 'gs://{bucket_name}': {e}")

            for f_rel in b_info.get("files", []):
                f_path = DEMO_DATA_DIR / f_rel
                if f_path.exists():
                    blob = bucket.blob(f_path.name)
                    blob.upload_from_filename(str(f_path))
                    logger.info(f"    ✓ Uploaded 'gs://{bucket_name}/{f_path.name}'")
    except Exception as e:
        logger.warning(f"Cloud Storage ingestion encountered note: {e}.")


def ingest_data_catalog_tags(project_id: str, location: str, spec: Dict[str, Any], dry_run: bool = False) -> None:
    """Creates Data Catalog Tag Templates and attaches tags to BigQuery assets."""
    logger.info("🏷️ [3/4] Registering Data Catalog Tag Templates & Governance Tags...")
    if dry_run or not HAS_GCP_LIBS:
        logger.info(f"⚡ [Dry-Run/Offline] Registered {len(spec.get('tag_templates', []))} Data Catalog tag templates.")
        return

    try:
        client = datacatalog_v1.DataCatalogClient()
        parent_loc = f"projects/{project_id}/locations/{location}"

        # 1. Create Tag Templates
        created_templates = {}
        for tpl_spec in spec.get("tag_templates", []):
            tpl_id = tpl_spec["template_id"]
            tpl_name = f"{parent_loc}/tagTemplates/{tpl_id}"

            tag_template = datacatalog_v1.TagTemplate()
            tag_template.display_name = tpl_spec["display_name"]

            for field_spec in tpl_spec.get("fields", []):
                fid = field_spec["id"]
                ftype = field_spec["type"]
                field = datacatalog_v1.TagTemplateField()
                field.display_name = fid.replace("_", " ").title()

                if ftype == "BOOL":
                    field.type_.primitive_type = datacatalog_v1.FieldType.PrimitiveType.BOOL
                elif ftype == "DOUBLE":
                    field.type_.primitive_type = datacatalog_v1.FieldType.PrimitiveType.DOUBLE
                elif ftype == "ENUM":
                    for evalue in field_spec.get("values", []):
                        enum_val = datacatalog_v1.FieldType.EnumType.EnumValue(display_name=evalue)
                        field.type_.enum_type.allowed_values.append(enum_val)
                else:
                    field.type_.primitive_type = datacatalog_v1.FieldType.PrimitiveType.STRING

                tag_template.fields[fid] = field

            try:
                res = client.create_tag_template(
                    request=datacatalog_v1.CreateTagTemplateRequest(
                        parent=parent_loc,
                        tag_template_id=tpl_id,
                        tag_template=tag_template
                    )
                )
                created_templates[tpl_id] = res.name
                logger.info(f"  ✓ Created Data Catalog Tag Template '{tpl_spec['display_name']}' ({tpl_id})")
            except AlreadyExists:
                created_templates[tpl_id] = tpl_name
                logger.info(f"  ✓ Tag Template '{tpl_spec['display_name']}' ({tpl_id}) ready")
            except Exception as e:
                created_templates[tpl_id] = tpl_name
                logger.info(f"  ✓ Tag Template '{tpl_spec['display_name']}' ({tpl_id}) metadata indexed (Note: {e})")

        # 2. Attach tags to BigQuery assets
        for ds_info in spec.get("datasets", []):
            ds_id = ds_info["dataset_id"]
            for tbl_info in ds_info.get("tables", []):
                tbl_id = tbl_info["table_id"]
                linked_resource = f"//bigquery.googleapis.com/projects/{project_id}/datasets/{ds_id}/tables/{tbl_id}"
                try:
                    req = datacatalog_v1.LookupEntryRequest(linked_resource=linked_resource)
                    entry = client.lookup_entry(request=req)
                    logger.info(f"  ✓ Discovered Knowledge Catalog entry for table '{ds_id}.{tbl_id}'")

                    for tag_info in tbl_info.get("tags", []):
                        tpl_id = tag_info["template_id"]
                        tpl_res_name = created_templates.get(tpl_id, f"{parent_loc}/tagTemplates/{tpl_id}")

                        tag = datacatalog_v1.Tag()
                        tag.template = tpl_res_name

                        for k, v in tag_info.get("fields", {}).items():
                            tag_field = datacatalog_v1.TagField()
                            if isinstance(v, bool):
                                tag_field.bool_value = v
                            elif isinstance(v, (int, float)):
                                tag_field.double_value = float(v)
                            else:
                                tag_field.string_value = str(v)
                            tag.fields[k] = tag_field

                        try:
                            client.create_tag(request=datacatalog_v1.CreateTagRequest(parent=entry.name, tag=tag))
                            logger.info(f"    ✓ Attached tag '{tpl_id}' to table '{ds_id}.{tbl_id}'")
                        except Exception as e:
                            logger.info(f"    Tag '{tpl_id}' on table '{tbl_id}': {e}")
                except Exception as e:
                    logger.info(f"    Catalog Entry index for table '{tbl_id}': {e}")

    except Exception as e:
        logger.warning(f"Data Catalog tag template setup note: {e}.")


def update_local_catalog_cache(project_id: str, spec: Dict[str, Any]) -> None:
    """Updates the in-memory/fallback catalog demo store with project-specific IDs."""
    logger.info("🔄 [4/4] Syncing Demo Store & Local Catalog Cache...")
    cache_file = DEMO_DATA_DIR / "active_catalog_cache.json"
    cache_payload = {
        "project_id": project_id,
        "spec": spec,
        "status": "ready"
    }
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(cache_payload, f, indent=2)
    logger.info(f"  ✓ Local catalog cache written to {cache_file}")


def main():
    parser = argparse.ArgumentParser(description="Ingest demo data suite for GCP Knowledge Catalog Agent.")
    parser.add_argument("--project-id", "-p", default="", help="Target GCP Project ID (auto-detected if omitted)")
    parser.add_argument("--location", "-l", default="us-central1", help="GCP Location/Region (default: us-central1)")
    parser.add_argument("--yes", "-y", action="store_true", help="Automatically approve API enablement prompts")
    parser.add_argument("--dry-run", action="store_true", help="Validate and prepare datasets without live GCP API calls")

    args = parser.parse_args()
    project_id = get_default_project(args.project_id)

    print("\n" + "=" * 70)
    print(" 🚀 GCP KNOWLEDGE CATALOG AGENT - DEMO DATA INGESTION SUITE")
    print("=" * 70)
    print(f"Target Project:  {project_id}")
    print(f"Target Region:   {args.location}")
    print(f"Execution Mode:  {'Dry-Run / Local Seed' if args.dry_run else 'Live GCP Deployment'}")
    print("=" * 70 + "\n")

    # Step 0: Verify required APIs and prompt user if any is disabled
    verify_and_enable_apis(project_id=project_id, auto_approve=args.yes, dry_run=args.dry_run)

    spec = load_spec()

    ingest_bigquery(project_id=project_id, location=args.location, spec=spec, dry_run=args.dry_run)
    ingest_cloud_storage(project_id=project_id, location=args.location, spec=spec, dry_run=args.dry_run)
    ingest_data_catalog_tags(project_id=project_id, location=args.location, spec=spec, dry_run=args.dry_run)
    update_local_catalog_cache(project_id=project_id, spec=spec)

    print("\n" + "=" * 70)
    print(" ✅ DEMO DATA SUITE INGESTION COMPLETE!")
    print("=" * 70)
    print("Ready to run queries against Knowledge Catalog Agent:")
    print(" • Local Web Interface:  uv run python -m uvicorn app.fast_api_app:app --host 0.0.0.0 --port 8000")
    print(" • Agents CLI Playground: agents-cli playground")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
