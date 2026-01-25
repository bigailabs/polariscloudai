"""
Storage Layer for Polaris Computer
Handles persistent user data with Storj (S3-compatible)

Key workflow:
1. User signs up → Create Storj bucket for user
2. Deployment starts → Mount user's storage volume
3. Deployment stops → Sync all data to Storj
4. Deployment restarts → Restore data from Storj

Storage structure:
storj://polaris-users/{user_id}/
  ├── apps/
  │   ├── ollama/models/
  │   ├── jupyter/notebooks/
  │   └── {template_id}/
  └── shared/
"""

import os
import asyncio
import hashlib
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path
from uuid import UUID

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

# Storj configuration from environment
STORJ_ACCESS_KEY = os.getenv("STORJ_ACCESS_KEY", "")
STORJ_SECRET_KEY = os.getenv("STORJ_SECRET_KEY", "")
STORJ_ENDPOINT = os.getenv("STORJ_ENDPOINT", "https://gateway.storjshare.io")
STORJ_BUCKET_PREFIX = os.getenv("STORJ_BUCKET_PREFIX", "polaris-users")
STORJ_REGION = os.getenv("STORJ_REGION", "us-east-1")

# Local cache directory for syncing
LOCAL_CACHE_DIR = os.getenv("STORAGE_CACHE_DIR", "/tmp/polaris-storage")


class StorageClient:
    """
    S3-compatible storage client for Storj.
    Handles user data persistence across deployment lifecycles.
    """

    def __init__(self):
        self.enabled = bool(STORJ_ACCESS_KEY and STORJ_SECRET_KEY)
        self._client = None

        if self.enabled:
            self._client = boto3.client(
                's3',
                endpoint_url=STORJ_ENDPOINT,
                aws_access_key_id=STORJ_ACCESS_KEY,
                aws_secret_access_key=STORJ_SECRET_KEY,
                region_name=STORJ_REGION,
                config=Config(
                    signature_version='s3v4',
                    retries={'max_attempts': 3, 'mode': 'adaptive'}
                )
            )

    @property
    def client(self):
        if not self._client:
            raise RuntimeError("Storage not configured. Set STORJ_ACCESS_KEY and STORJ_SECRET_KEY.")
        return self._client

    def get_bucket_name(self, user_id: UUID) -> str:
        """Generate bucket name for a user"""
        # Use a hash prefix for better distribution
        prefix = hashlib.sha256(str(user_id).encode()).hexdigest()[:8]
        return f"{STORJ_BUCKET_PREFIX}-{prefix}"

    def get_user_prefix(self, user_id: UUID) -> str:
        """Get the S3 key prefix for a user's data"""
        return f"{user_id}/"

    async def create_user_storage(self, user_id: UUID) -> Dict[str, Any]:
        """
        Create storage bucket and folder structure for a new user.
        Called during user signup.
        """
        if not self.enabled:
            return {"success": False, "error": "Storage not configured"}

        bucket_name = self.get_bucket_name(user_id)
        user_prefix = self.get_user_prefix(user_id)

        try:
            # Create bucket if it doesn't exist
            try:
                self.client.head_bucket(Bucket=bucket_name)
            except ClientError as e:
                if e.response['Error']['Code'] == '404':
                    self.client.create_bucket(Bucket=bucket_name)
                else:
                    raise

            # Create folder structure markers
            folders = [
                f"{user_prefix}apps/",
                f"{user_prefix}apps/ollama/models/",
                f"{user_prefix}apps/jupyter/notebooks/",
                f"{user_prefix}shared/",
            ]

            for folder in folders:
                self.client.put_object(
                    Bucket=bucket_name,
                    Key=folder,
                    Body=b''
                )

            return {
                "success": True,
                "bucket_name": bucket_name,
                "user_prefix": user_prefix,
                "storage_path": f"s3://{bucket_name}/{user_prefix}"
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_storage_usage(self, user_id: UUID) -> Dict[str, Any]:
        """Calculate total storage used by a user"""
        if not self.enabled:
            return {"size_bytes": 0, "file_count": 0}

        bucket_name = self.get_bucket_name(user_id)
        user_prefix = self.get_user_prefix(user_id)

        try:
            total_size = 0
            file_count = 0

            paginator = self.client.get_paginator('list_objects_v2')
            for page in paginator.paginate(Bucket=bucket_name, Prefix=user_prefix):
                for obj in page.get('Contents', []):
                    total_size += obj['Size']
                    file_count += 1

            return {
                "size_bytes": total_size,
                "file_count": file_count,
                "bucket_name": bucket_name
            }

        except Exception as e:
            return {"size_bytes": 0, "file_count": 0, "error": str(e)}

    async def sync_to_storage(
        self,
        user_id: UUID,
        template_id: str,
        local_path: str,
        host: str,
        ssh_user: str = "root"
    ) -> Dict[str, Any]:
        """
        Sync data from a running deployment to Storj.
        Called when a deployment is stopped.

        Args:
            user_id: User's UUID
            template_id: Template being synced (ollama, jupyter, etc.)
            local_path: Path on the remote host to sync
            host: Remote host IP/hostname
            ssh_user: SSH user for remote connection
        """
        if not self.enabled:
            return {"success": False, "error": "Storage not configured"}

        bucket_name = self.get_bucket_name(user_id)
        s3_prefix = f"{self.get_user_prefix(user_id)}apps/{template_id}/"

        try:
            # Create local cache directory
            cache_dir = Path(LOCAL_CACHE_DIR) / str(user_id) / template_id
            cache_dir.mkdir(parents=True, exist_ok=True)

            # Sync from remote host to local cache via rsync over SSH
            rsync_cmd = f"rsync -avz --delete -e 'ssh -o StrictHostKeyChecking=no' {ssh_user}@{host}:{local_path}/ {cache_dir}/"

            process = await asyncio.create_subprocess_shell(
                rsync_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                return {
                    "success": False,
                    "error": f"rsync failed: {stderr.decode()}"
                }

            # Upload to Storj
            uploaded_files = 0
            uploaded_bytes = 0

            for file_path in cache_dir.rglob('*'):
                if file_path.is_file():
                    relative_path = file_path.relative_to(cache_dir)
                    s3_key = f"{s3_prefix}{relative_path}"

                    self.client.upload_file(
                        str(file_path),
                        bucket_name,
                        s3_key
                    )
                    uploaded_files += 1
                    uploaded_bytes += file_path.stat().st_size

            return {
                "success": True,
                "files_uploaded": uploaded_files,
                "bytes_uploaded": uploaded_bytes,
                "storage_path": f"s3://{bucket_name}/{s3_prefix}"
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def restore_from_storage(
        self,
        user_id: UUID,
        template_id: str,
        local_path: str,
        host: str,
        ssh_user: str = "root"
    ) -> Dict[str, Any]:
        """
        Restore data from Storj to a deployment.
        Called when a deployment starts.

        Args:
            user_id: User's UUID
            template_id: Template being restored
            local_path: Path on the remote host to restore to
            host: Remote host IP/hostname
            ssh_user: SSH user for remote connection
        """
        if not self.enabled:
            return {"success": False, "error": "Storage not configured"}

        bucket_name = self.get_bucket_name(user_id)
        s3_prefix = f"{self.get_user_prefix(user_id)}apps/{template_id}/"

        try:
            # Create local cache directory
            cache_dir = Path(LOCAL_CACHE_DIR) / str(user_id) / template_id
            cache_dir.mkdir(parents=True, exist_ok=True)

            # Download from Storj to local cache
            downloaded_files = 0
            downloaded_bytes = 0

            paginator = self.client.get_paginator('list_objects_v2')
            for page in paginator.paginate(Bucket=bucket_name, Prefix=s3_prefix):
                for obj in page.get('Contents', []):
                    s3_key = obj['Key']
                    relative_path = s3_key[len(s3_prefix):]

                    if not relative_path or relative_path.endswith('/'):
                        continue

                    local_file = cache_dir / relative_path
                    local_file.parent.mkdir(parents=True, exist_ok=True)

                    self.client.download_file(
                        bucket_name,
                        s3_key,
                        str(local_file)
                    )
                    downloaded_files += 1
                    downloaded_bytes += obj['Size']

            if downloaded_files == 0:
                return {
                    "success": True,
                    "message": "No existing data to restore",
                    "files_restored": 0
                }

            # Sync from local cache to remote host
            rsync_cmd = f"rsync -avz -e 'ssh -o StrictHostKeyChecking=no' {cache_dir}/ {ssh_user}@{host}:{local_path}/"

            process = await asyncio.create_subprocess_shell(
                rsync_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                return {
                    "success": False,
                    "error": f"rsync failed: {stderr.decode()}"
                }

            return {
                "success": True,
                "files_restored": downloaded_files,
                "bytes_restored": downloaded_bytes
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def delete_user_storage(self, user_id: UUID) -> Dict[str, Any]:
        """
        Delete all storage for a user.
        Called when user account is deleted.
        """
        if not self.enabled:
            return {"success": False, "error": "Storage not configured"}

        bucket_name = self.get_bucket_name(user_id)
        user_prefix = self.get_user_prefix(user_id)

        try:
            # List and delete all objects with user prefix
            deleted_count = 0
            paginator = self.client.get_paginator('list_objects_v2')

            for page in paginator.paginate(Bucket=bucket_name, Prefix=user_prefix):
                objects = page.get('Contents', [])
                if objects:
                    delete_request = {
                        'Objects': [{'Key': obj['Key']} for obj in objects]
                    }
                    self.client.delete_objects(
                        Bucket=bucket_name,
                        Delete=delete_request
                    )
                    deleted_count += len(objects)

            return {
                "success": True,
                "deleted_objects": deleted_count
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def list_user_files(
        self,
        user_id: UUID,
        template_id: Optional[str] = None,
        path: str = ""
    ) -> Dict[str, Any]:
        """List files in user's storage"""
        if not self.enabled:
            return {"files": [], "error": "Storage not configured"}

        bucket_name = self.get_bucket_name(user_id)

        if template_id:
            prefix = f"{self.get_user_prefix(user_id)}apps/{template_id}/{path}"
        else:
            prefix = f"{self.get_user_prefix(user_id)}{path}"

        try:
            files = []
            paginator = self.client.get_paginator('list_objects_v2')

            for page in paginator.paginate(Bucket=bucket_name, Prefix=prefix, Delimiter='/'):
                # Add folders
                for prefix_obj in page.get('CommonPrefixes', []):
                    folder_name = prefix_obj['Prefix'].rstrip('/').split('/')[-1]
                    files.append({
                        "name": folder_name,
                        "type": "folder",
                        "path": prefix_obj['Prefix']
                    })

                # Add files
                for obj in page.get('Contents', []):
                    if obj['Key'] != prefix:  # Skip the prefix itself
                        file_name = obj['Key'].split('/')[-1]
                        if file_name:  # Skip empty names (folders)
                            files.append({
                                "name": file_name,
                                "type": "file",
                                "size": obj['Size'],
                                "modified": obj['LastModified'].isoformat(),
                                "path": obj['Key']
                            })

            return {"files": files, "prefix": prefix}

        except Exception as e:
            return {"files": [], "error": str(e)}

    async def get_download_url(
        self,
        user_id: UUID,
        file_path: str,
        expires_in: int = 3600
    ) -> Optional[str]:
        """Generate a presigned URL for downloading a file"""
        if not self.enabled:
            return None

        bucket_name = self.get_bucket_name(user_id)

        try:
            url = self.client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': bucket_name,
                    'Key': file_path
                },
                ExpiresIn=expires_in
            )
            return url
        except Exception:
            return None

    async def get_upload_url(
        self,
        user_id: UUID,
        file_path: str,
        expires_in: int = 3600
    ) -> Optional[str]:
        """Generate a presigned URL for uploading a file"""
        if not self.enabled:
            return None

        bucket_name = self.get_bucket_name(user_id)
        full_path = f"{self.get_user_prefix(user_id)}{file_path}"

        try:
            url = self.client.generate_presigned_url(
                'put_object',
                Params={
                    'Bucket': bucket_name,
                    'Key': full_path
                },
                ExpiresIn=expires_in
            )
            return url
        except Exception:
            return None


# Template-specific storage paths
TEMPLATE_STORAGE_PATHS = {
    "ollama": {
        "data_path": "/root/.ollama",
        "description": "Ollama models and configuration"
    },
    "jupyter": {
        "data_path": "/home/jovyan/work",
        "description": "Jupyter notebooks and data"
    },
    "dev-terminal": {
        "data_path": "/workspace",
        "description": "Development workspace files"
    },
    "transformer-labs": {
        "data_path": "/home/abc/workspace",
        "description": "Transformer Lab models and configs"
    },
    "ubuntu-desktop": {
        "data_path": "/home/kasm-user",
        "description": "Desktop user home directory"
    },
    "minecraft": {
        "data_path": "/data",
        "description": "Minecraft world and server data"
    },
    "valheim": {
        "data_path": "/config",
        "description": "Valheim world and configuration"
    },
    "terraria": {
        "data_path": "/config",
        "description": "Terraria world data"
    },
    "factorio": {
        "data_path": "/factorio",
        "description": "Factorio saves and mods"
    }
}


def get_template_storage_path(template_id: str) -> Optional[str]:
    """Get the data path for a template that should be persisted"""
    template_config = TEMPLATE_STORAGE_PATHS.get(template_id)
    return template_config["data_path"] if template_config else None


# Global storage client instance
storage_client = StorageClient()
