#!/usr/bin/env python3
"""
Verda Serverless Container Deployment
Deploy TTS server with auto-scaling and spot instances
"""
import requests
import json
import time
import os

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Verda API Configuration
VERDA_CLIENT_ID = os.getenv("VERDA_CLIENT_ID", "")
VERDA_CLIENT_SECRET = os.getenv("VERDA_CLIENT_SECRET", "")
VERDA_API_BASE = "https://api.verda.com/v1"

class VerdaClient:
    def __init__(self, client_id, client_secret):
        self.client_id = client_id
        self.client_secret = client_secret
        self.token = None
        self.token_expires = 0
        self.authenticate()

    def authenticate(self):
        """Get OAuth2 token"""
        print("🔐 Authenticating with Verda...")

        response = requests.post(
            f"{VERDA_API_BASE}/oauth2/token",
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret
            }
        )

        if response.status_code == 200:
            data = response.json()
            self.token = data["access_token"]
            self.token_expires = time.time() + data.get("expires_in", 3600)
            print("✅ Authenticated successfully")
        else:
            print(f"❌ Auth failed: {response.status_code} - {response.text}")
            raise Exception("Authentication failed")

    def get_headers(self):
        # Refresh token if expired
        if time.time() >= self.token_expires - 300:  # Refresh 5 min before expiry
            self.authenticate()

        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    def create_container_deployment(
        self,
        name="tts-server",
        image="ghcr.io/wallscaler/chatterbox-tts:v1.0.0",
        gpu_type="Tesla V100 16GB",  # Cheapest serverless: $0.076/hour spot
        use_spot=True
    ):
        """
        Create a serverless container deployment with spot instances

        Args:
            name: Deployment name
            image: Docker image
            gpu_type: GPU type (e.g., "Tesla V100 16GB", "A100 SXM4 40GB")
            use_spot: Use spot instances for cheaper pricing
        """
        print(f"\n🚀 Creating container deployment: {name}")
        print(f"   Image: {image}")
        print(f"   GPU: {gpu_type}")
        print(f"   Spot Instances: {'Yes' if use_spot else 'No'}")

        # Get HF token from environment
        hf_token = os.getenv("HF_TOKEN", "")
        if not hf_token:
            print("⚠️  Warning: HF_TOKEN not set in environment")

        deployment_config = {
            "name": name,
            "container_registry_settings": {
                "is_private": False  # Public GitHub Container Registry image
            },
            "containers": [
                {
                    "image": image,
                    "exposed_port": 8000,
                    "environment_variables": {
                        "HF_TOKEN": hf_token,
                        "TTS_PORT": "8000",
                        "CORS_ORIGINS": "*"
                    }
                }
            ],
            "compute": {
                "name": gpu_type,  # Use the GPU type parameter (not hardcoded!)
                "size": 1  # Number of GPUs
            },
            "scaling": {
                "min_replica_count": 0,  # Scale to zero when idle
                "max_replica_count": 3,  # Scale up to 3 under load
                "queue_message_ttl_seconds": 3600,  # Queue messages expire after 1 hour
                "concurrent_requests_per_replica": 1,  # Handle 1 request at a time per replica
                "scaling_triggers": {
                    "queue_load": {
                        "threshold": 1  # Scale up when queue has 1+ items
                    }
                },
                "scale_up_policy": {
                    "delay_seconds": 30  # Wait 30s before scaling up
                },
                "scale_down_policy": {
                    "delay_seconds": 900  # 15 min idle before scale down
                }
            },
            "is_spot": use_spot  # Spot instances at top level
        }

        response = requests.post(
            f"{VERDA_API_BASE}/container-deployments",
            headers=self.get_headers(),
            json=deployment_config
        )

        if response.status_code in [200, 201]:
            deployment = response.json()
            print(f"✅ Deployment created successfully!")
            return deployment
        else:
            print(f"❌ Failed to create deployment:")
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.text}")
            return None

    def get_deployment_status(self, name):
        """Check deployment status"""
        response = requests.get(
            f"{VERDA_API_BASE}/container-deployments/{name}/status",
            headers=self.get_headers()
        )

        if response.status_code == 200:
            return response.json()
        return None

    def get_deployment(self, name):
        """Get full deployment details"""
        response = requests.get(
            f"{VERDA_API_BASE}/container-deployments/{name}",
            headers=self.get_headers()
        )

        if response.status_code == 200:
            return response.json()
        return None

    def list_deployments(self):
        """List all deployments"""
        response = requests.get(
            f"{VERDA_API_BASE}/container-deployments",
            headers=self.get_headers()
        )

        if response.status_code == 200:
            return response.json()
        return []

    def get_available_gpus(self):
        """
        Get available GPU types with pricing from Verda API.

        Returns:
            List of dicts sorted by serverless spot price (cheapest first):
            [
                {
                    "name": "Tesla V100 16GB",
                    "display_name": "Tesla V100 16GB",
                    "serverless_spot_price": 0.076,
                    "instance_spot_price": 0.050,
                    "memory": "16GB",
                    "description": "Best value (cheapest)"
                },
                ...
            ]
        """
        try:
            response = requests.get(
                f"{VERDA_API_BASE}/instance-types",
                headers=self.get_headers()
            )

            if response.status_code == 200:
                data = response.json()
                gpus = []

                # Handle both dict and string items from API
                for item in data:
                    # Skip if item is not a dict (might be a string)
                    if not isinstance(item, dict):
                        continue

                    name = item.get("name", "")

                    # ONLY include single-GPU instances
                    # Check both the name (skip "2x", "4x", etc.) AND the gpu.number_of_gpus field
                    gpu_info = item.get("gpu", {})
                    num_gpus = gpu_info.get("number_of_gpus", 1) if isinstance(gpu_info, dict) else 1

                    if num_gpus != 1:
                        continue

                    if any(prefix in name for prefix in ["2x", "4x", "8x", "16x"]):
                        continue

                    # Filter for GPU instances only
                    if "GPU" in item.get("description", "") or any(
                        gpu in name for gpu in ["V100", "A100", "H100", "L40", "A6000", "RTX", "B200", "B300", "GB300", "H200"]
                    ):
                        # NEW API FORMAT (as of 2026-01):
                        # - serverless_price: direct float like "5.995"
                        # - serverless_spot_price: direct float like "1.499"
                        # - price_per_hour: direct float like "5.450"
                        # - spot_price: direct float like "1.363" (THIS IS WHAT WE WANT for raw compute)
                        # - gpu_memory.size_in_gigabytes: int like 288

                        # Get serverless spot price (string to float)
                        serverless_spot_str = item.get("serverless_spot_price", 0)
                        serverless_spot = float(serverless_spot_str) if serverless_spot_str else 0

                        # Get instance spot price (THIS IS THE RAW COMPUTE PRICE)
                        instance_spot_str = item.get("spot_price", 0)
                        instance_spot = float(instance_spot_str) if instance_spot_str else 0

                        # Get GPU memory from gpu_memory dict
                        gpu_memory_dict = item.get("gpu_memory", {})
                        memory_gb = gpu_memory_dict.get("size_in_gigabytes", "?") if isinstance(gpu_memory_dict, dict) else "?"

                        # Get instance_type (like "1V100.6V") and supported OS images
                        instance_type = item.get("instance_type", "")
                        supported_os = item.get("supported_os", [])

                        gpus.append({
                            "name": name,
                            "display_name": name,
                            "instance_type": instance_type,  # Required for raw compute instances
                            "supported_os": supported_os,     # Valid OS images for this GPU
                            "serverless_spot_price": serverless_spot,
                            "instance_spot_price": instance_spot,  # Raw compute spot price
                            "memory": str(memory_gb) + "GB",
                            "description": item.get("description", "")
                        })

                # Remove duplicates (same name + same price) - keep first occurrence
                seen = set()
                unique_gpus = []
                for gpu in gpus:
                    key = (gpu['name'], gpu['instance_spot_price'])
                    if key not in seen:
                        seen.add(key)
                        unique_gpus.append(gpu)

                # Sort by instance spot price (cheapest first) - since we're using raw compute
                if unique_gpus and len(unique_gpus) > 0:
                    # Check if we got valid data (prices > 0)
                    valid_prices = sum(1 for g in unique_gpus if g['instance_spot_price'] > 0)
                    if valid_prices > 0:
                        return sorted(unique_gpus, key=lambda x: x['instance_spot_price'])
                    else:
                        # API returned data but all prices are 0 - use fallback
                        print("⚠️ API returned invalid pricing data, using fallback list")

        except Exception as e:
            print(f"⚠️ Failed to fetch GPUs from API: {e}")

        # Fallback to known GPUs - RAW COMPUTE INSTANCE PRICING (from Verda API)
        # These are SPOT PRICES for raw compute instances (not serverless)
        DEFAULT_GPUS = [
            {
                "name": "Tesla V100 16GB",
                "display_name": "Tesla V100 16GB",
                "serverless_spot_price": 0.076,  # Serverless container price
                "instance_spot_price": 0.076,    # Raw instance spot price
                "memory": "16GB",
                "description": "Best value (cheapest)"
            },
            {
                "name": "RTX A6000 48GB",
                "display_name": "RTX A6000 48GB",
                "serverless_spot_price": 0.162,
                "instance_spot_price": 0.162,
                "memory": "48GB",
                "description": "Professional GPU"
            },
            {
                "name": "A100 SXM4 40GB",
                "display_name": "A100 SXM4 40GB",
                "serverless_spot_price": 0.238,
                "instance_spot_price": 0.238,
                "memory": "40GB",
                "description": "High performance"
            },
            {
                "name": "RTX 6000 Ada 48GB",
                "display_name": "RTX 6000 Ada 48GB",
                "serverless_spot_price": 0.273,
                "instance_spot_price": 0.273,
                "memory": "48GB",
                "description": "Professional graphics"
            },
            {
                "name": "L40S 48GB",
                "display_name": "L40S 48GB",
                "serverless_spot_price": 0.302,
                "instance_spot_price": 0.302,
                "memory": "48GB",
                "description": "Professional GPU"
            },
            {
                "name": "RTX PRO 6000 96GB",
                "display_name": "RTX PRO 6000 96GB",
                "serverless_spot_price": 0.382,
                "instance_spot_price": 0.382,
                "memory": "96GB",
                "description": "High memory professional"
            },
            {
                "name": "A100 SXM4 80GB",
                "display_name": "A100 SXM4 80GB",
                "serverless_spot_price": 0.638,
                "instance_spot_price": 0.638,
                "memory": "80GB",
                "description": "High memory compute"
            },
            {
                "name": "B200 SXM6 180GB",
                "display_name": "B200 SXM6 180GB",
                "serverless_spot_price": 1.042,
                "instance_spot_price": 1.042,
                "memory": "180GB",
                "description": "Ultra high memory"
            },
            {
                "name": "H100 SXM5 80GB",
                "display_name": "H100 SXM5 80GB",
                "serverless_spot_price": 1.095,
                "instance_spot_price": 1.095,
                "memory": "80GB",
                "description": "Highest performance"
            },
            {
                "name": "B300 SXM6 262GB",
                "display_name": "B300 SXM6 262GB",
                "serverless_spot_price": 1.361,
                "instance_spot_price": 1.361,
                "memory": "262GB",
                "description": "Extreme memory"
            },
            {
                "name": "GB300 SXM6 288GB",
                "display_name": "GB300 SXM6 288GB",
                "serverless_spot_price": 1.499,
                "instance_spot_price": 1.499,
                "memory": "288GB",
                "description": "Maximum memory"
            },
            {
                "name": "H200 SXM5 141GB",
                "display_name": "H200 SXM5 141GB",
                "serverless_spot_price": 1.645,
                "instance_spot_price": 1.645,
                "memory": "141GB",
                "description": "Latest generation"
            }
        ]

        # Return sorted by serverless spot_price (cheapest first)
        return sorted(DEFAULT_GPUS, key=lambda x: x['serverless_spot_price'])

    def delete_deployment(self, name, wait=True):
        """Delete a deployment"""
        print(f"\n🗑️  Deleting deployment: {name}")

        params = {"wait": wait}
        response = requests.delete(
            f"{VERDA_API_BASE}/container-deployments/{name}",
            headers=self.get_headers(),
            params=params
        )

        if response.status_code in [200, 204]:
            print("✅ Deployment deleted")
            return True
        else:
            print(f"❌ Delete failed: {response.text}")
            return False

    # ========== Raw Compute Instance Methods ==========

    def create_instance(
        self,
        name="tts-server-compute",
        gpu_name="Tesla V100 16GB",
        use_spot=True,
        ssh_public_key=None
    ):
        """
        Create a raw compute instance with SSH access.

        Args:
            name: Instance hostname
            gpu_name: GPU display name (e.g., "Tesla V100 16GB")
            use_spot: Use spot instances
            ssh_public_key: User's SSH public key (optional, uses account keys if not provided)

        Returns:
            Instance details including SSH connection info
        """
        # Get GPU details from API to find instance_type and supported OS
        gpus = self.get_available_gpus()
        gpu_data = next((g for g in gpus if g['name'] == gpu_name), None)

        if not gpu_data:
            print(f"❌ GPU '{gpu_name}' not found in available GPUs")
            return None

        instance_type = gpu_data.get('instance_type')
        supported_os = gpu_data.get('supported_os', [])

        if not instance_type:
            print(f"❌ No instance_type found for {gpu_name}")
            return None

        # Choose a supported OS image (prefer ubuntu with docker)
        os_image = None
        for os_name in supported_os:
            if 'docker' in os_name.lower():
                os_image = os_name
                break
        if not os_image and supported_os:
            os_image = supported_os[0]  # Use first available

        if not os_image:
            print(f"❌ No supported OS found for {gpu_name}")
            return None

        print(f"\n🚀 Creating compute instance: {name}")
        print(f"   GPU: {gpu_name}")
        print(f"   Instance Type: {instance_type}")
        print(f"   OS Image: {os_image}")
        print(f"   Spot: {'Yes' if use_spot else 'No'}")

        # Handle SSH key - either use provided key or account keys
        ssh_key_ids = []
        if ssh_public_key:
            print(f"   SSH Key: User-provided")
            key_id = self.find_or_create_ssh_key(ssh_public_key)
            if key_id:
                ssh_key_ids = [key_id]
            else:
                print("⚠️  Warning: Failed to add SSH key, trying account keys")
                ssh_key_ids = self.get_ssh_key_ids()
        else:
            # Get SSH key IDs from account
            ssh_key_ids = self.get_ssh_key_ids()

        if not ssh_key_ids:
            print("⚠️  Warning: No SSH keys found")

        instance_config = {
            "hostname": name,
            "instance_type": instance_type,  # Use instance_type like "1V100.6V"
            "is_spot": use_spot,
            "image": os_image,  # Use supported OS image
            "description": f"TTS server on {gpu_name}",
            "startup_script": f"""#!/bin/bash
# Set up environment
export HF_TOKEN={hf_token}
export TTS_PORT=8000
export CORS_ORIGINS=*

# Install Docker if not present
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
fi

# Pull and run Docker container
docker pull ghcr.io/wallscaler/chatterbox-tts:v1.1.0
docker run -d --gpus all \\
  -p 8000:8000 \\
  -e HF_TOKEN=$HF_TOKEN \\
  -e TTS_PORT=$TTS_PORT \\
  -e CORS_ORIGINS=$CORS_ORIGINS \\
  --restart unless-stopped \\
  --name tts-server \\
  ghcr.io/wallscaler/chatterbox-tts:v1.1.0

echo "TTS server started on port 8000"
"""
        }

        # Add SSH keys if available
        if ssh_key_ids:
            instance_config["ssh_key_ids"] = ssh_key_ids  # Note: ssh_key_ids not ssh_keys!

        response = requests.post(
            f"{VERDA_API_BASE}/instances",
            headers=self.get_headers(),
            json=instance_config
        )

        if response.status_code in [200, 201, 202]:
            # 202 means accepted - instance ID in response text
            if response.status_code == 202:
                instance_id = response.text.strip().strip('"')
                print(f"✅ Instance creation started!")
                print(f"   Instance ID: {instance_id}")
                # Wait a moment then fetch details
                time.sleep(3)
                return self.get_instance(instance_id)
            else:
                instance = response.json()
                print(f"✅ Instance created!")
                print(f"   Instance ID: {instance.get('id')}")
                print(f"   IP: {instance.get('ip', 'pending...')}")
                return instance
        else:
            print(f"❌ Failed: {response.status_code}")
            print(f"   {response.text}")
            return None

    def get_ssh_key_ids(self):
        """Get list of SSH key IDs from account"""
        try:
            response = requests.get(
                f"{VERDA_API_BASE}/ssh-keys",
                headers=self.get_headers()
            )
            if response.status_code == 200:
                keys = response.json()
                return [key['id'] for key in keys if isinstance(key, dict)]
            return []
        except:
            return []

    def add_ssh_key(self, name: str, public_key: str):
        """
        Add an SSH public key to the account.

        Args:
            name: Name/label for the key
            public_key: The SSH public key string (e.g., "ssh-rsa AAAA...")

        Returns:
            The key ID if successful, None otherwise
        """
        try:
            response = requests.post(
                f"{VERDA_API_BASE}/ssh-keys",
                headers=self.get_headers(),
                json={
                    "name": name,
                    "public_key": public_key
                }
            )
            if response.status_code in [200, 201]:
                key_data = response.json()
                return key_data.get('id')
            else:
                print(f"⚠️ Failed to add SSH key: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"⚠️ Failed to add SSH key: {e}")
            return None

    def find_or_create_ssh_key(self, public_key: str):
        """
        Find existing SSH key by public key content or create new one.

        Args:
            public_key: The SSH public key string

        Returns:
            The key ID
        """
        try:
            # Get all existing keys
            response = requests.get(
                f"{VERDA_API_BASE}/ssh-keys",
                headers=self.get_headers()
            )
            if response.status_code == 200:
                keys = response.json()
                # Check if key already exists (compare the key content)
                for key in keys:
                    if isinstance(key, dict):
                        # Compare public key content (might be stored differently)
                        existing_key = key.get('public_key', '')
                        if existing_key and public_key.strip().startswith(existing_key.strip()[:50]):
                            return key.get('id')

            # Key not found, create new one
            key_name = f"polaris-{int(time.time())}"
            return self.add_ssh_key(key_name, public_key)
        except Exception as e:
            print(f"⚠️ Error finding/creating SSH key: {e}")
            return None

    def get_instance(self, instance_id):
        """Get instance details"""
        response = requests.get(
            f"{VERDA_API_BASE}/instances/{instance_id}",
            headers=self.get_headers()
        )

        if response.status_code == 200:
            return response.json()
        return None

    def list_instances(self):
        """List all compute instances"""
        response = requests.get(
            f"{VERDA_API_BASE}/instances",
            headers=self.get_headers()
        )

        if response.status_code == 200:
            return response.json()
        return []

    def delete_instance(self, instance_id):
        """Delete a compute instance using Verda SDK"""
        try:
            from verda import VerdaClient as SDKClient

            # Create SDK client
            sdk_client = SDKClient(self.client_id, self.client_secret)

            # Use SDK's action method to delete
            print(f"\n🗑️  Deleting instance: {instance_id}")
            sdk_client.instances.action(instance_id, 'delete')
            print("✅ Instance deleted")
            return True
        except Exception as e:
            print(f"❌ Delete failed: {e}")
            return False

    # ========== Health Check Methods ==========

    def wait_for_healthy(self, name, timeout=600):
        """Wait for deployment to become healthy"""
        print(f"\n⏳ Waiting for deployment to be healthy...")
        start = time.time()

        while time.time() - start < timeout:
            status = self.get_deployment_status(name)

            if status:
                state = status.get("status", "unknown")
                print(f"   Container Status: {state}")

                if state == "healthy":
                    print("✅ Container is healthy!")
                    return True
                elif state in ["unhealthy", "failed"]:
                    print(f"❌ Deployment failed: {state}")
                    return False

            time.sleep(15)

        print("❌ Timeout waiting for container to be healthy")
        return False

    def wait_for_application_ready(self, endpoint, timeout=300):
        """
        Wait for application to be ready (two-tier health check)

        Args:
            endpoint: Base URL of the deployment
            timeout: Maximum time to wait in seconds

        Returns:
            True if application becomes ready, False otherwise
        """
        print(f"\n⏳ Waiting for application to be ready...")
        print(f"   Checking: {endpoint}/ready")

        start = time.time()
        attempt = 0

        # Exponential backoff: 5s, 10s, 15s, 30s, 30s...
        backoff_intervals = [5, 10, 15, 30]

        while time.time() - start < timeout:
            attempt += 1

            try:
                response = requests.get(
                    f"{endpoint}/ready",
                    timeout=10,
                    allow_redirects=True
                )

                if response.status_code == 200:
                    data = response.json()
                    if data.get("ready"):
                        elapsed = time.time() - start
                        print(f"✅ Application ready! (took {elapsed:.1f}s)")

                        # Also check /health for full status
                        try:
                            health_resp = requests.get(f"{endpoint}/health", timeout=5)
                            if health_resp.status_code == 200:
                                health_data = health_resp.json()
                                print(f"   Model: {health_data.get('model', 'unknown')}")
                                print(f"   Device: {health_data.get('device', 'unknown')}")
                        except:
                            pass

                        return True
                elif response.status_code == 503:
                    # Service unavailable - still loading
                    data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
                    loading_time = data.get('detail', {}).get('loading_time_seconds', 'unknown')
                    print(f"   Attempt {attempt}: Still loading... ({loading_time}s)")
                else:
                    print(f"   Attempt {attempt}: Unexpected status {response.status_code}")

            except requests.exceptions.ConnectionError:
                print(f"   Attempt {attempt}: Container not accessible yet, waiting...")
            except requests.exceptions.Timeout:
                print(f"   Attempt {attempt}: Request timeout, container may be busy...")
            except Exception as e:
                print(f"   Attempt {attempt}: Error - {str(e)[:100]}")

            # Calculate wait time with exponential backoff
            wait_time = backoff_intervals[min(attempt-1, len(backoff_intervals)-1)]

            # Don't wait if we're out of time
            if time.time() - start + wait_time > timeout:
                break

            time.sleep(wait_time)

        elapsed = time.time() - start
        print(f"❌ Application not ready after {elapsed:.1f}s")
        print(f"   The model may still be downloading or loading.")
        print(f"   Try checking {endpoint}/health manually in a few minutes.")
        return False


def main():
    """Deploy TTS server on Verda serverless containers"""

    print("=" * 60)
    print("Verda Serverless TTS Deployment")
    print("=" * 60)

    # Initialize client
    client = VerdaClient(VERDA_CLIENT_ID, VERDA_CLIENT_SECRET)

    # List existing deployments
    print("\n📋 Checking existing deployments...")
    deployments = client.list_deployments()
    if deployments:
        print(f"   Found {len(deployments)} existing deployment(s)")
        for dep in deployments:
            print(f"   - {dep.get('name')}: {dep.get('status')}")

    # Create new deployment
    gpu_choice = "A100 40GB"  # Cheapest spot option at $0.238/hour
    use_spot_instances = True

    deployment = client.create_container_deployment(
        name="tts-server-spot",
        image="ghcr.io/wallscaler/chatterbox-tts:v1.0.0",
        gpu_type=gpu_choice,
        use_spot=use_spot_instances
    )

    if not deployment:
        print("\n❌ Deployment failed. Exiting.")
        return

    deployment_name = deployment.get("name")

    # Two-tier health check
    # Tier 1: Wait for container to be healthy
    if client.wait_for_healthy(deployment_name):
        # Get full deployment info
        details = client.get_deployment(deployment_name)

        if details:
            endpoint = details.get("endpoint_base_url")

            # Tier 2: Wait for application to be ready
            app_ready = client.wait_for_application_ready(endpoint, timeout=300)

            if not app_ready:
                print("\n⚠️  Container is healthy but application not ready yet.")
                print(f"   The model may still be loading. Check {endpoint}/health later.")

            print(f"\n" + "=" * 60)
            print(f"🎉 TTS Server Deployed Successfully!")
            print(f"=" * 60)
            print(f"📍 Endpoint: {endpoint}")
            print(f"💰 Cost: $0.238/hour ({gpu_choice} spot)")
            print(f"⚡ Auto-scales: 0-3 replicas")
            print(f"🔄 Scale to zero after 15 min idle")
            print(f"=" * 60)

            # Save deployment info
            with open("verda_deployment.json", "w") as f:
                json.dump({
                    "name": deployment_name,
                    "endpoint": endpoint,
                    "gpu_type": gpu_choice,
                    "spot": use_spot_instances,
                    "created_at": time.time()
                }, f, indent=2)

            print(f"\n💾 Deployment info saved to: verda_deployment.json")

            # Test endpoint
            if endpoint:
                print(f"\n🧪 Testing endpoint...")
                try:
                    health_url = f"{endpoint}/health"
                    print(f"   GET {health_url}")
                    response = requests.get(health_url, timeout=30)
                    print(f"   ✅ Response: {response.json()}")
                except Exception as e:
                    print(f"   ⚠️  Test failed (may need time to start): {e}")
                    print(f"   Try: curl {endpoint}/health")

    print(f"\n📖 To delete this deployment:")
    print(f"   python verda_deploy.py --delete {deployment_name}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--delete":
        if len(sys.argv) < 3:
            print("Usage: python verda_deploy.py --delete <deployment-name>")
            sys.exit(1)

        deployment_name = sys.argv[2]
        client = VerdaClient(VERDA_CLIENT_ID, VERDA_CLIENT_SECRET)
        client.delete_deployment(deployment_name)
    elif len(sys.argv) > 1 and sys.argv[1] == "--list":
        client = VerdaClient(VERDA_CLIENT_ID, VERDA_CLIENT_SECRET)
        deployments = client.list_deployments()
        print(f"\n📋 Deployments ({len(deployments)}):")
        for dep in deployments:
            print(f"   - {dep.get('name')}: {dep.get('status')}")
    else:
        main()
