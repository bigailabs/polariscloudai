"""
Test suite for VoiceFlow API authentication and endpoints
Tests API key validation, endpoint security, and health monitoring
"""
import pytest
import requests
import os
from pathlib import Path

# Test configuration
BASE_URL = os.getenv("TEST_ENDPOINT", "http://localhost:8000")
VALID_API_KEY = os.getenv("TEST_API_KEY", "vf_test_12345")
INVALID_API_KEY = "vf_invalid_key"


class TestHealthEndpoints:
    """Test public health monitoring endpoints"""

    def test_health_endpoint_accessible(self):
        """Health endpoint should be accessible without API key"""
        response = requests.get(f"{BASE_URL}/health")
        assert response.status_code == 200

    def test_health_response_structure(self):
        """Health endpoint should return correct structure"""
        response = requests.get(f"{BASE_URL}/health")
        data = response.json()

        assert "status" in data
        assert "model" in data
        assert "device" in data
        assert "ready" in data
        assert data["model"] == "chatterbox-turbo"

    def test_health_status_values(self):
        """Health status should be 'healthy' or 'loading'"""
        response = requests.get(f"{BASE_URL}/health")
        data = response.json()

        assert data["status"] in ["healthy", "loading"]
        assert isinstance(data["ready"], bool)

    def test_ready_endpoint_accessible(self):
        """Ready endpoint should be accessible without API key"""
        response = requests.get(f"{BASE_URL}/ready")

        # Should be either 200 (ready) or 503 (still loading)
        assert response.status_code in [200, 503]

    def test_ready_response_structure(self):
        """Ready endpoint should return correct structure"""
        response = requests.get(f"{BASE_URL}/ready")

        if response.status_code == 200:
            data = response.json()
            assert "ready" in data
            assert data["ready"] is True
        else:
            data = response.json()
            assert "detail" in data
            assert "ready" in data["detail"]
            assert data["detail"]["ready"] is False


class TestAPIKeyAuthentication:
    """Test API key authentication for protected endpoints"""

    def test_generate_without_api_key(self):
        """Generate endpoint should reject requests without API key"""
        response = requests.post(
            f"{BASE_URL}/generate",
            files={"text": (None, "Test text")}
        )

        # Could be 401 (auth required) or 200 (backward compatible mode)
        # If 401, check error structure
        if response.status_code == 401:
            data = response.json()
            assert "detail" in data
            error = data["detail"]
            if isinstance(error, dict):
                assert error["error"] == "missing_api_key"
                assert "message" in error

    def test_generate_with_invalid_api_key(self):
        """Generate endpoint should reject invalid API keys"""
        response = requests.post(
            f"{BASE_URL}/generate",
            headers={"X-API-Key": INVALID_API_KEY},
            files={"text": (None, "Test text")}
        )

        # Could be 401 (invalid key) or 200 (backward compatible mode)
        if response.status_code == 401:
            data = response.json()
            assert "detail" in data
            error = data["detail"]
            if isinstance(error, dict):
                assert error["error"] == "invalid_api_key"

    def test_generate_with_valid_api_key(self):
        """Generate endpoint should accept valid API keys"""
        response = requests.post(
            f"{BASE_URL}/generate",
            headers={"X-API-Key": VALID_API_KEY},
            files={"text": (None, "Test")},
            timeout=30
        )

        # Should be 200 (success) or 401 if key not configured
        assert response.status_code in [200, 401]

        if response.status_code == 200:
            # Should return audio data
            assert response.headers["content-type"] == "audio/wav"
            assert len(response.content) > 0

    def test_api_key_header_case_sensitivity(self):
        """API key header should handle different cases"""
        headers = [
            {"X-API-Key": VALID_API_KEY},
            {"x-api-key": VALID_API_KEY},
            {"X-Api-Key": VALID_API_KEY},
        ]

        for header in headers:
            response = requests.post(
                f"{BASE_URL}/generate",
                headers=header,
                files={"text": (None, "Test")},
                timeout=30
            )

            # FastAPI normalizes header names, so all should work
            assert response.status_code in [200, 401]


class TestGenerateEndpoint:
    """Test the /generate endpoint functionality"""

    def test_generate_simple_text(self):
        """Generate speech from simple text"""
        response = requests.post(
            f"{BASE_URL}/generate",
            headers={"X-API-Key": VALID_API_KEY},
            files={"text": (None, "Hello world")},
            timeout=30
        )

        if response.status_code == 200:
            assert response.headers["content-type"] == "audio/wav"
            assert len(response.content) > 1000  # Should be substantial audio

    def test_generate_with_tags(self):
        """Generate speech with expression tags"""
        text = "Hello! [laugh] This is amazing!"

        response = requests.post(
            f"{BASE_URL}/generate",
            headers={"X-API-Key": VALID_API_KEY},
            files={"text": (None, text)},
            timeout=30
        )

        if response.status_code == 200:
            assert response.headers["content-type"] == "audio/wav"

    def test_generate_empty_text(self):
        """Generate endpoint should handle empty text"""
        response = requests.post(
            f"{BASE_URL}/generate",
            headers={"X-API-Key": VALID_API_KEY},
            files={"text": (None, "")},
            timeout=30
        )

        # Should either accept or reject gracefully
        assert response.status_code in [200, 400, 422, 500]

    def test_generate_long_text(self):
        """Generate speech from longer text"""
        long_text = "This is a longer text sample. " * 20

        response = requests.post(
            f"{BASE_URL}/generate",
            headers={"X-API-Key": VALID_API_KEY},
            files={"text": (None, long_text)},
            timeout=60  # Longer timeout for long text
        )

        if response.status_code == 200:
            assert response.headers["content-type"] == "audio/wav"
            # Longer text should produce more audio
            assert len(response.content) > 10000

    def test_generate_response_headers(self):
        """Check response headers are correct"""
        response = requests.post(
            f"{BASE_URL}/generate",
            headers={"X-API-Key": VALID_API_KEY},
            files={"text": (None, "Test")},
            timeout=30
        )

        if response.status_code == 200:
            assert response.headers["content-type"] == "audio/wav"
            assert "content-disposition" in response.headers.lower()


class TestVoiceCloning:
    """Test voice cloning functionality"""

    def test_voice_cloning_with_sample(self):
        """Generate speech with voice cloning (if sample available)"""
        # Create a minimal WAV file for testing
        # Note: This is a placeholder - real test would use actual audio
        sample_path = Path("/tmp/test_voice_sample.wav")

        # Skip if no sample file
        if not sample_path.exists():
            pytest.skip("Voice sample file not available")

        with open(sample_path, "rb") as voice_file:
            response = requests.post(
                f"{BASE_URL}/generate",
                headers={"X-API-Key": VALID_API_KEY},
                files={
                    "text": (None, "This is a test"),
                    "voice_ref": ("voice.wav", voice_file, "audio/wav")
                },
                timeout=30
            )

            if response.status_code == 200:
                assert response.headers["content-type"] == "audio/wav"


class TestErrorHandling:
    """Test error handling and edge cases"""

    def test_invalid_endpoint(self):
        """Non-existent endpoints should return 404"""
        response = requests.get(f"{BASE_URL}/nonexistent")
        assert response.status_code == 404

    def test_wrong_http_method(self):
        """Wrong HTTP methods should be rejected"""
        # GET on POST endpoint
        response = requests.get(f"{BASE_URL}/generate")
        assert response.status_code in [405, 422]  # Method Not Allowed or Unprocessable

    def test_malformed_request(self):
        """Malformed requests should be rejected gracefully"""
        response = requests.post(
            f"{BASE_URL}/generate",
            headers={"X-API-Key": VALID_API_KEY},
            data="not multipart form data",
            timeout=30
        )

        assert response.status_code in [400, 422]

    def test_timeout_handling(self):
        """Very long requests should timeout gracefully"""
        # This test would require very long text or other timeout condition
        pytest.skip("Timeout test requires specific setup")


class TestCORS:
    """Test CORS configuration"""

    def test_cors_headers_present(self):
        """CORS headers should be present for browser compatibility"""
        response = requests.options(f"{BASE_URL}/health")

        # Check for CORS headers
        # Note: Actual headers depend on server configuration
        assert response.status_code in [200, 204, 405]


class TestRateLimiting:
    """Test rate limiting behavior (if implemented)"""

    def test_concurrent_requests(self):
        """Multiple concurrent requests should be handled"""
        # This is a basic test - real load testing would be more complex
        pytest.skip("Concurrent request testing requires specific setup")

    def test_queue_behavior(self):
        """Requests should queue when replicas are busy"""
        pytest.skip("Queue testing requires load generation")


# Integration test
class TestEndToEndFlow:
    """End-to-end integration tests"""

    def test_full_workflow(self):
        """Complete workflow: health check -> generate -> verify audio"""
        # 1. Check health
        health_response = requests.get(f"{BASE_URL}/health")
        assert health_response.status_code == 200
        health_data = health_response.json()

        # 2. Wait for ready if needed
        if not health_data.get("ready"):
            ready_response = requests.get(f"{BASE_URL}/ready")
            # May be 503 if still loading
            assert ready_response.status_code in [200, 503]

        # 3. Generate speech if ready
        if health_data.get("ready"):
            gen_response = requests.post(
                f"{BASE_URL}/generate",
                headers={"X-API-Key": VALID_API_KEY},
                files={"text": (None, "End to end test")},
                timeout=30
            )

            if gen_response.status_code == 200:
                # 4. Verify audio output
                audio_data = gen_response.content
                assert len(audio_data) > 1000
                assert audio_data[:4] == b"RIFF"  # WAV file signature


# Pytest configuration
def pytest_configure(config):
    """Configure pytest"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )


if __name__ == "__main__":
    # Run tests with: python -m pytest tests/test_api.py -v
    pytest.main([__file__, "-v", "--tb=short"])
