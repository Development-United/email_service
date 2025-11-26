"""
Unit tests for the email service API
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock
import os

# Set test environment variables before importing app
os.environ["EMAIL_PASSWORD"] = "test_password"
os.environ["ENVIRONMENT"] = "testing"

from app import app
from models import EmailRequest


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def sample_email_request():
    """Sample email request data"""
    return {
        "user_name": "John Doe",
        "user_email": "john.doe@example.com",
        "meeting_time": "Thursday, November 30th at 2:00 PM EST",
    }


class TestHealthEndpoints:
    """Tests for health and monitoring endpoints"""

    def test_root_endpoint(self, client):
        """Test root endpoint returns service info"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"
        assert "version" in data
        assert "service" in data

    def test_health_endpoint(self, client):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "email_configured" in data
        assert "version" in data

    def test_metrics_endpoint(self, client):
        """Test metrics endpoint"""
        response = client.get("/metrics")
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert "version" in data


class TestEmailEndpoint:
    """Tests for email sending endpoint"""

    @patch("email_service.EmailService.send_email_async")
    async def test_send_email_success(self, mock_send, client, sample_email_request):
        """Test successful email sending"""
        # Mock successful email send
        mock_send.return_value = {
            "success": True,
            "message": "Email successfully sent",
            "recipient": sample_email_request["user_email"],
        }

        response = client.post("/api/v1/send-email", json=sample_email_request)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["recipient"] == sample_email_request["user_email"]
        assert "request_id" in data
        assert "timestamp" in data

    def test_send_email_invalid_email(self, client, sample_email_request):
        """Test email validation"""
        sample_email_request["user_email"] = "invalid-email"

        response = client.post("/api/v1/send-email", json=sample_email_request)

        assert response.status_code == 422
        data = response.json()
        assert data["error"] == "validation_error"

    def test_send_email_empty_name(self, client, sample_email_request):
        """Test empty user name validation"""
        sample_email_request["user_name"] = "   "

        response = client.post("/api/v1/send-email", json=sample_email_request)

        assert response.status_code == 422

    def test_send_email_missing_fields(self, client):
        """Test missing required fields"""
        response = client.post("/api/v1/send-email", json={})

        assert response.status_code == 422

    def test_request_id_in_response(self, client, sample_email_request):
        """Test that request ID is included in response"""
        with patch("email_service.EmailService.send_email_async") as mock_send:
            mock_send.return_value = {
                "success": True,
                "message": "Email sent",
                "recipient": sample_email_request["user_email"],
            }

            response = client.post("/api/v1/send-email", json=sample_email_request)

            assert "x-request-id" in response.headers
            data = response.json()
            assert "request_id" in data


class TestRateLimiting:
    """Tests for rate limiting functionality"""

    def test_rate_limit_headers(self, client):
        """Test that rate limiting adds appropriate headers"""
        response = client.get("/")
        assert "x-process-time" in response.headers

    @pytest.mark.parametrize("endpoint", ["/", "/health", "/docs"])
    def test_public_endpoints_no_rate_limit(self, client, endpoint):
        """Test that public endpoints are not rate limited"""
        # Make multiple requests
        for _ in range(15):
            response = client.get(endpoint)
            assert response.status_code != 429


class TestSecurityHeaders:
    """Tests for security headers"""

    def test_security_headers_present(self, client):
        """Test that security headers are added to responses"""
        response = client.get("/")

        assert "x-content-type-options" in response.headers
        assert response.headers["x-content-type-options"] == "nosniff"

        assert "x-frame-options" in response.headers
        assert response.headers["x-frame-options"] == "DENY"

        assert "x-xss-protection" in response.headers


class TestModels:
    """Tests for Pydantic models"""

    def test_email_request_validation(self, sample_email_request):
        """Test EmailRequest model validation"""
        request = EmailRequest(**sample_email_request)
        assert request.user_name == sample_email_request["user_name"].strip()
        assert request.user_email == sample_email_request["user_email"]

    def test_email_request_strip_whitespace(self):
        """Test that whitespace is stripped from inputs"""
        request = EmailRequest(
            user_name="  John Doe  ",
            user_email="john@example.com",
            meeting_time="  Tomorrow at 2pm  ",
        )
        assert request.user_name == "John Doe"
        assert request.meeting_time == "Tomorrow at 2pm"

    def test_email_request_invalid_email(self, sample_email_request):
        """Test invalid email validation"""
        sample_email_request["user_email"] = "not-an-email"
        with pytest.raises(ValueError):
            EmailRequest(**sample_email_request)


class TestErrorHandling:
    """Tests for error handling"""

    @patch("email_service.EmailService.send_email_async")
    async def test_smtp_connection_error(self, mock_send, client, sample_email_request):
        """Test SMTP connection error handling"""
        from exceptions import SMTPConnectionError

        mock_send.side_effect = SMTPConnectionError("Connection failed")

        response = client.post("/api/v1/send-email", json=sample_email_request)

        assert response.status_code == 502
        data = response.json()
        assert data["error"] == "smtp_connection_error"

    @patch("email_service.EmailService.send_email_async")
    async def test_email_send_error(self, mock_send, client, sample_email_request):
        """Test email send error handling"""
        from exceptions import EmailSendError

        mock_send.side_effect = EmailSendError("Failed to send")

        response = client.post("/api/v1/send-email", json=sample_email_request)

        assert response.status_code == 500
        data = response.json()
        assert data["error"] == "email_send_error"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
