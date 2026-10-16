"""
upload_to_databricks.py
-----------------------
Uploads local Parquet batches to a Unity Catalog Volume using the
Databricks SDK. Designed to be idempotent: re-running will overwrite
files of the same name rather than duplicating them.
"""
import os
from pathlib import Path

from databricks.sdk import WorkspaceClient
from dotenv import load_dotenv


def get_workspace_client() -> WorkspaceClient:
    """Initialise the SDK using the profile from .env (OAuth-based)."""
    load_dotenv()
    profile = os.getenv("DATABRICKS_CONFIG_PROFILE")
    return WorkspaceClient(profile=profile) if profile else WorkspaceClient()


def get_volume_path() -> str:
    """Build the Unity Catalog volume path from .env values."""
    catalog = os.getenv("DATABRICKS_CATALOG")
    schema = os.getenv("DATABRICKS_SCHEMA")
    volume = os.getenv("DATABRICKS_VOLUME")
    return f"/Volumes/{catalog}/{schema}/{volume}"


def upload_batch(local_file: Path, remote_dir: str, client: WorkspaceClient) -> None:
    """
    Upload a single Parquet file to the volume.
    Uses the SDK's upload_from, which is atomic and overwrites by default.
    """
    remote_path = f"{remote_dir}/{local_file.name}"

    with open(local_file, "rb") as f:
        client.files.upload(remote_path, f, overwrite=True)

    size_kb = local_file.stat().st_size / 1024
    print(f"  ✓ {local_file.name} ({size_kb:,.1f} KB) → {remote_path}")


def upload_all_batches(local_dir: str = "data/raw") -> None:
    """Upload every Parquet file in the local directory to the volume."""
    load_dotenv()
    client = get_workspace_client()
    remote_dir = f"{get_volume_path()}/raw"

    # Ensure the destination subfolder exists
    client.files.create_directory(remote_dir)

    local_path = Path(local_dir)
    parquet_files = sorted(local_path.glob("*.parquet"))

    if not parquet_files:
        print(f"No Parquet files found in {local_dir}/")
        return

    print(f"Uploading {len(parquet_files)} file(s) to {remote_dir}")
    for f in parquet_files:
        upload_batch(f, remote_dir, client)

    print(f"\nDone. All files uploaded to {remote_dir}")


def list_remote_files() -> None:
    """List files currently in the volume's raw/ directory for verification."""
    load_dotenv()
    client = get_workspace_client()
    remote_dir = f"{get_volume_path()}/raw"

    print(f"Contents of {remote_dir}:")
    for f in client.files.list_directory_contents(remote_dir):
        size_mb = (f.file_size or 0) / (1024 * 1024)
        print(f"  - {f.name} ({size_mb:.2f} MB)")


if __name__ == "__main__":
    upload_all_batches()
    print()
    list_remote_files()