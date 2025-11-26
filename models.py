"""
Pydantic models for request/response validation
"""
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from datetime import datetime


class EmailRequest(BaseModel):
    """Request model for sending emails"""
    user_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Name of the user"
    )
    user_email: EmailStr = Field(
        ...,
        description="Email address of the user"
    )
    meeting_time: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Scheduled meeting time"
    )

    @validator('user_name')
    def validate_user_name(cls, v):
        """Validate user name doesn't contain only whitespace"""
        if not v.strip():
            raise ValueError("User name cannot be empty or contain only whitespace")
        return v.strip()

    @validator('meeting_time')
    def validate_meeting_time(cls, v):
        """Validate meeting time is not empty"""
        if not v.strip():
            raise ValueError("Meeting time cannot be empty")
        return v.strip()

    class Config:
        json_schema_extra = {
            "example": {
                "user_name": "John Doe",
                "user_email": "john.doe@example.com",
                "meeting_time": "Thursday, November 30th at 2:00 PM EST"
            }
        }


class EmailResponse(BaseModel):
    """Response model for email sending"""
    success: bool = Field(..., description="Whether the email was sent successfully")
    message: str = Field(..., description="Status message")
    recipient: Optional[str] = Field(None, description="Email recipient")
    request_id: Optional[str] = Field(None, description="Request tracking ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Email successfully sent to john.doe@example.com",
                "recipient": "john.doe@example.com",
                "request_id": "req_123456789",
                "timestamp": "2025-01-26T12:00:00Z"
            }
        }


class HealthResponse(BaseModel):
    """Health check response model"""
    status: str = Field(..., description="Service status")
    version: str = Field(..., description="API version")
    environment: str = Field(..., description="Environment name")
    email_configured: bool = Field(..., description="Whether email service is configured")
    smtp_reachable: Optional[bool] = Field(None, description="Whether SMTP server is reachable")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ErrorResponse(BaseModel):
    """Error response model"""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    request_id: Optional[str] = Field(None, description="Request tracking ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
