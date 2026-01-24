#!/usr/bin/env python3
"""
Targon GPU Cloud Client
Integrates with Targon's Rentals API for GPU compute instances.

Based on Targon documentation:
- Rentals are dedicated, persistent containers with SSH access
- Connect via: ssh <RENTAL_ID>@ssh.deployments.targon.com
"""

import os
import httpx
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv

load_dotenv()

TARGON_API_KEY = os.getenv("TARGON_API_KEY", "")
TARGON_API_BASE = "https://api.targon.com"

# Targon GPU offerings (based on documentation mentioning H200, etc.)
# Prices are estimates - will be updated when API returns real data
TARGON_GPU_CATALOG = [
    {"name": "H100 SXM5 80GB", "display_name": "H100 (Targon)", "memory": "80GB", "base_price": 1.45, "resource": "h100-small"},
    {"name": "H200 SXM5 141GB", "display_name": "H200 (Targon)", "memory": "141GB", "base_price": 2.25, "resource": "h200-small"},
]


class TargonClient:
    """Client for Targon GPU cloud API"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        self.authenticated = False
        self._authenticate()

    def _authenticate(self):
        """Verify API key is valid"""
        if not self.api_key:
            print("⚠️  No Targon API key provided")
            return

        try:
            # Try to list rentals to verify authentication
            with httpx.Client(timeout=10.0) as client:
                response = client.get(
                    f"{TARGON_API_BASE}/v1/rentals",
                    headers=self.headers
                )
                if response.status_code == 200:
                    self.authenticated = True
                    print("✅ Targon authenticated successfully")
                elif response.status_code == 401:
                    print("❌ Targon authentication failed: Invalid API key")
                else:
                    print(f"⚠️  Targon API returned status {response.status_code}")
        except Exception as e:
            print(f"⚠️  Could not verify Targon authentication: {e}")

    def get_available_gpus(self) -> List[Dict[str, Any]]:
        """Get available GPU types from Targon"""
        gpus = []

        if not self.authenticated:
            # Return catalog with availability unknown
            for gpu in TARGON_GPU_CATALOG:
                gpus.append({
                    "name": gpu["name"],
                    "display_name": gpu["display_name"],
                    "memory": gpu["memory"],
                    "instance_spot_price": gpu["base_price"],
                    "available_count": None,  # Unknown
                    "provider": "targon",
                    "resource": gpu["resource"]
                })
            return gpus

        try:
            # Try to get GPU availability from Targon API
            with httpx.Client(timeout=10.0) as client:
                response = client.get(
                    f"{TARGON_API_BASE}/v1/gpus",
                    headers=self.headers
                )
                if response.status_code == 200:
                    data = response.json()
                    for gpu in data.get("gpus", []):
                        gpus.append({
                            "name": gpu.get("name", "Unknown"),
                            "display_name": gpu.get("display_name", gpu.get("name", "Unknown")),
                            "memory": gpu.get("memory", "N/A"),
                            "instance_spot_price": gpu.get("price_per_hour", 0),
                            "available_count": gpu.get("available", None),
                            "provider": "targon",
                            "resource": gpu.get("resource", "")
                        })
                    return gpus
        except Exception as e:
            print(f"Error fetching Targon GPUs: {e}")

        # Fallback to catalog
        for gpu in TARGON_GPU_CATALOG:
            gpus.append({
                "name": gpu["name"],
                "display_name": gpu["display_name"],
                "memory": gpu["memory"],
                "instance_spot_price": gpu["base_price"],
                "available_count": None,
                "provider": "targon",
                "resource": gpu["resource"]
            })
        return gpus

    def list_instances(self) -> List[Dict[str, Any]]:
        """List active rentals/instances"""
        if not self.authenticated:
            return []

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(
                    f"{TARGON_API_BASE}/v1/rentals",
                    headers=self.headers
                )
                if response.status_code == 200:
                    data = response.json()
                    instances = []
                    for rental in data.get("rentals", []):
                        instances.append({
                            "id": rental.get("id"),
                            "name": rental.get("name", rental.get("id", "Unknown")),
                            "gpu_type": rental.get("gpu_type", "Unknown"),
                            "status": rental.get("status", "unknown"),
                            "ip": None,  # Targon uses SSH gateway instead
                            "ssh_command": f"ssh {rental.get('id')}@ssh.deployments.targon.com",
                            "hourly_cost": rental.get("price_per_hour", 0),
                            "provider": "targon"
                        })
                    return instances
        except Exception as e:
            print(f"Error listing Targon instances: {e}")

        return []

    def create_instance(
        self,
        name: str,
        gpu_type: str,
        ssh_public_key: str,
        image: str = "ubuntu:22.04"
    ) -> Optional[Dict[str, Any]]:
        """Create a new rental instance on Targon"""
        if not self.authenticated:
            print("Cannot create Targon instance: not authenticated")
            return None

        try:
            # Find the resource type for this GPU
            resource = None
            for gpu in TARGON_GPU_CATALOG:
                if gpu["name"] == gpu_type or gpu["display_name"] == gpu_type:
                    resource = gpu["resource"]
                    break

            if not resource:
                resource = "h100-small"  # Default

            payload = {
                "name": name,
                "image": image,
                "resource": resource,
                "ssh_keys": [ssh_public_key]
            }

            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    f"{TARGON_API_BASE}/v1/rentals",
                    headers=self.headers,
                    json=payload
                )

                if response.status_code in (200, 201):
                    data = response.json()
                    rental = data.get("rental", data)
                    return {
                        "id": rental.get("id"),
                        "name": name,
                        "status": rental.get("status", "starting"),
                        "ssh_command": f"ssh {rental.get('id')}@ssh.deployments.targon.com",
                        "provider": "targon"
                    }
                else:
                    print(f"Targon create failed: {response.status_code} - {response.text}")
                    return None

        except Exception as e:
            print(f"Error creating Targon instance: {e}")
            return None

    def delete_instance(self, instance_id: str) -> bool:
        """Terminate a rental instance"""
        if not self.authenticated:
            return False

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.delete(
                    f"{TARGON_API_BASE}/v1/rentals/{instance_id}",
                    headers=self.headers
                )
                return response.status_code in (200, 204)
        except Exception as e:
            print(f"Error deleting Targon instance: {e}")
            return False


# Test the client
if __name__ == "__main__":
    client = TargonClient(TARGON_API_KEY)
    print("\nAvailable GPUs:")
    for gpu in client.get_available_gpus():
        print(f"  - {gpu['display_name']}: ${gpu['instance_spot_price']}/hr")
