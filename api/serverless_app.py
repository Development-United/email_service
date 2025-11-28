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
from typing import Optional, Tuple
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel, EmailStr, Field, validator
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import os
import uuid
import dateparser
import pytz

# Environment variables with defaults
ENVIRONMENT = os.getenv("ENVIRONMENT", "production")
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "tech@asklena.ai")
SENDER_NAME = os.getenv("SENDER_NAME", "Lena (AskLena.AI)")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
EMAIL_TIMEOUT = int(os.getenv("EMAIL_TIMEOUT", "30"))
HOST_EMAIL = os.getenv("HOST_EMAIL", "chitraksha@asklena.ai")
PERMANENT_MEETING_LINK = os.getenv("PERMANENT_MEETING_LINK", "https://meet.google.com/igx-icor-cnz")
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

def parse_meeting_time(raw_time_string: str) -> Tuple[Optional[datetime], Optional[datetime]]:
    """
    Converts human string (e.g., "Nov 29th 5pm PST") into a strict UTC datetime object.
    """
    settings = {
        'TIMEZONE': 'US/Pacific',
        'RETURN_AS_TIMEZONE_AWARE': True
    }

    dt = dateparser.parse(raw_time_string, settings=settings)

    if not dt:
        return None, None

    # Calculate End Time (15 minute meeting)
    dt_end = dt + timedelta(minutes=15)

    # Convert both to UTC (Computer Time) for the ICS file
    dt_start_utc = dt.astimezone(pytz.utc)
    dt_end_utc = dt_end.astimezone(pytz.utc)

    return dt_start_utc, dt_end_utc

def generate_ics_content(user_name: str, user_email: str, start_utc: datetime, end_utc: datetime) -> str:
    """
    Creates the text content for the .ics calendar file.
    """
    # Formatting time as YYYYMMDDTHHMMSSZ
    fmt = "%Y%m%dT%H%M%SZ"
    start_str = start_utc.strftime(fmt)
    end_str = end_utc.strftime(fmt)
    now_str = datetime.now(timezone.utc).strftime(fmt)
    unique_id = str(uuid.uuid4())

    meet_link = PERMANENT_MEETING_LINK

    # The ICS Body with attendees
    ics_body = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Ask Lena AI//Voice Agent//EN
METHOD:REQUEST
BEGIN:VEVENT
UID:{unique_id}
DTSTAMP:{now_str}
DTSTART:{start_str}
DTEND:{end_str}
SUMMARY:Voice AI Strategy Call: {user_name} <> Ask Lena
DESCRIPTION:Hi {user_name},\\n\\nThis is the technical discovery call you booked with Lena.\\n\\nHost: Chitraksha ({HOST_EMAIL})\\n\\nJoin the Google Meet here: {meet_link}
LOCATION:{meet_link}
ORGANIZER;CN=Ask Lena AI:mailto:{SENDER_EMAIL}
ATTENDEE;ROLE=REQ-PARTICIPANT;RSVP=TRUE;CN={user_name}:mailto:{user_email}
ATTENDEE;ROLE=REQ-PARTICIPANT;RSVP=TRUE;CN=Chitraksha:mailto:{HOST_EMAIL}
STATUS:CONFIRMED
END:VEVENT
END:VCALENDAR"""

    return ics_body

def send_email_sync(user_name: str, user_email: str, meeting_time: str) -> dict:
    """Send email synchronously with calendar invite"""
    try:
        # Parse meeting time
        start_utc, end_utc = parse_meeting_time(meeting_time)
        if not start_utc:
            raise HTTPException(status_code=400, detail=f"Could not parse meeting time: {meeting_time}")

        # Load and personalize template
        html_content = load_email_template()
        personalized_html = html_content.replace("{user_name}", user_name)
        personalized_html = personalized_html.replace("{meeting_time}", meeting_time)
        personalized_html = personalized_html.replace("{GOOGLE_MEET_LINK_HERE}", PERMANENT_MEETING_LINK)

        # Create message with mixed content type for ICS attachment
        msg = MIMEMultipart("mixed")
        msg["Subject"] = f"Invitation: Tech Discovery Call with {user_name}"
        msg["From"] = f"{SENDER_NAME} <{SENDER_EMAIL}>"
        msg["To"] = user_email
        msg["Cc"] = HOST_EMAIL

        # Create HTML part
        msg_html = MIMEMultipart("alternative")
        msg_html.attach(MIMEText(personalized_html, "html"))
        msg.attach(msg_html)

        # Generate and attach ICS file
        ics_content = generate_ics_content(user_name, user_email, start_utc, end_utc)
        part_ics = MIMEBase("text", "calendar", method="REQUEST", name="invite.ics")
        part_ics.set_payload(ics_content)
        encoders.encode_base64(part_ics)
        part_ics.add_header('Content-Description', 'Meeting Invitation')
        part_ics.add_header('Content-class', 'urn:content-classes:calendarmessage')
        msg.attach(part_ics)

        # Send email to both user and host
        recipients = [user_email, HOST_EMAIL]
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=EMAIL_TIMEOUT)
        server.starttls()
        server.login(SENDER_EMAIL, EMAIL_PASSWORD)
        server.sendmail(SENDER_EMAIL, recipients, msg.as_string())
        server.quit()

        return {
            "success": True,
            "message": f"Email successfully sent to {user_email} (and copied {HOST_EMAIL})",
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
