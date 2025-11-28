"""
Serverless-optimized FastAPI application
Simplified version without lifespan events that cause issues in serverless
"""
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, validator
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os

# Environment variables with defaults
ENVIRONMENT = os.getenv("ENVIRONMENT", "production")
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "tech@asklena.ai")
SENDER_NAME = os.getenv("SENDER_NAME", "Lena (AskLena.AI)")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
EMAIL_TIMEOUT = int(os.getenv("EMAIL_TIMEOUT", "30"))
CORS_ORIGINS_STR = os.getenv("CORS_ORIGINS", '["*"]')

# Parse CORS origins
try:
    import json
    CORS_ORIGINS = json.loads(CORS_ORIGINS_STR)
except:
    CORS_ORIGINS = ["*"]

# Pydantic models
class EmailRequest(BaseModel):
    user_name: str = Field(..., min_length=1, max_length=100)
    user_email: EmailStr
    meeting_time: str = Field(..., min_length=1, max_length=200)

    @validator('user_name', 'meeting_time')
    def strip_whitespace(cls, v):
        return v.strip()

class EmailResponse(BaseModel):
    success: bool
    message: str
    recipient: Optional[str] = None
    request_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
    email_configured: bool
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class ErrorResponse(BaseModel):
    error: str
    message: str
    request_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

# Initialize FastAPI app
app = FastAPI(
    title="Email Service API",
    description="Production-ready API for sending confirmation emails",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def load_email_template() -> str:
    """Load email template from file"""
    parent_dir = Path(__file__).parent.parent
    template_path = parent_dir / "email_template.html"

    if not template_path.exists():
        raise FileNotFoundError(f"Email template not found: {template_path}")

    return template_path.read_text(encoding="utf-8")

def send_email_sync(user_name: str, user_email: str, meeting_time: str) -> dict:
    """Send email synchronously"""
    try:
        # Load and personalize template
        html_content = load_email_template()
        personalized_html = html_content.replace("{user_name}", user_name)
        personalized_html = personalized_html.replace("{meeting_time}", meeting_time)

        # Create message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"Confirmation: Tech Discovery Call with {user_name}"
        msg["From"] = f"{SENDER_NAME} <{SENDER_EMAIL}>"
        msg["To"] = user_email

        # Plain text fallback
        text_content = f"Hi {user_name}, your meeting is confirmed for {meeting_time}."
        text_part = MIMEText(text_content, "plain")
        html_part = MIMEText(personalized_html, "html")

        msg.attach(text_part)
        msg.attach(html_part)

        # Send email
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=EMAIL_TIMEOUT)
        server.starttls()
        server.login(SENDER_EMAIL, EMAIL_PASSWORD)
        server.sendmail(SENDER_EMAIL, user_email, msg.as_string())
        server.quit()

        return {
            "success": True,
            "message": f"Email successfully sent to {user_email}",
            "recipient": user_email
        }

    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=f"Email template not found: {str(e)}")
    except smtplib.SMTPAuthenticationError as e:
        raise HTTPException(status_code=502, detail=f"SMTP authentication failed: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")

# Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(
            error="validation_error",
            message="Invalid request data"
        ).model_dump(),
    )

# Routes
@app.get("/", tags=["General"])
async def root():
    """Root endpoint"""
    return {
        "service": "Email Service API",
        "version": "1.0.0",
        "status": "running",
        "environment": ENVIRONMENT,
        "docs": "/docs",
    }

@app.get("/health", response_model=HealthResponse, tags=["Monitoring"])
async def health_check():
    """Health check endpoint"""
    email_configured = bool(EMAIL_PASSWORD)

    return HealthResponse(
        status="healthy",
        version="1.0.0",
        environment=ENVIRONMENT,
        email_configured=email_configured,
    )

@app.post(
    "/api/v1/send-email",
    response_model=EmailResponse,
    status_code=status.HTTP_200_OK,
    tags=["Email"],
)
async def send_email(request: Request, email_request: EmailRequest):
    """Send a confirmation email"""

    # Check if email service is configured
    if not EMAIL_PASSWORD:
        raise HTTPException(
            status_code=500,
            detail="Email service not configured. EMAIL_PASSWORD environment variable is missing."
        )

    # Send email
    result = send_email_sync(
        user_name=email_request.user_name,
        user_email=email_request.user_email,
        meeting_time=email_request.meeting_time
    )

    return EmailResponse(
        success=result["success"],
        message=result["message"],
        recipient=result["recipient"],
    )

@app.get("/metrics", tags=["Monitoring"])
async def metrics():
    """Metrics endpoint"""
    return {
        "service": "Email Service API",
        "version": "1.0.0",
        "environment": ENVIRONMENT,
    }

# For Vercel
app = app
