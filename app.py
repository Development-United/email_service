"""
Production-ready FastAPI application for email service
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from config import get_settings
from models import EmailRequest, EmailResponse, HealthResponse, ErrorResponse
from email_service import get_email_service
from exceptions import (
    EmailTemplateNotFoundError,
    EmailSendError,
    SMTPConnectionError,
    ConfigurationError,
    RateLimitExceeded,
)
from middleware import (
    RequestIDMiddleware,
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
)
from logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan event handler for startup and shutdown

    Validates configuration and initializes services on startup
    """
    settings = get_settings()
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Environment: {settings.environment}")

    # Validate email service on startup
    try:
        email_service = get_email_service()
        logger.info("Email service initialized successfully")
    except EmailTemplateNotFoundError as e:
        logger.error(f"Failed to initialize email service: {e}")
        raise ConfigurationError(f"Email template not found: {e}")
    except Exception as e:
        logger.error(f"Unexpected error during startup: {e}")
        raise

    yield

    # Cleanup on shutdown
    logger.info("Shutting down application")


# Initialize FastAPI app
settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    description="Production-ready API for sending confirmation emails with retry logic, rate limiting, and monitoring",
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Add middleware (order matters - first added is outermost)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(RequestIDMiddleware)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)


# Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors"""
    request_id = getattr(request.state, "request_id", None)
    logger.warning(f"Validation error: {exc}", extra={"request_id": request_id})

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(
            error="validation_error",
            message="Invalid request data",
            request_id=request_id,
        ).model_dump(),
    )


@app.exception_handler(EmailTemplateNotFoundError)
async def template_not_found_handler(request: Request, exc: EmailTemplateNotFoundError):
    """Handle template not found errors"""
    request_id = getattr(request.state, "request_id", None)
    logger.error(f"Template not found: {exc}", extra={"request_id": request_id})

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="template_not_found",
            message=str(exc),
            request_id=request_id,
        ).model_dump(),
    )


@app.exception_handler(SMTPConnectionError)
async def smtp_connection_handler(request: Request, exc: SMTPConnectionError):
    """Handle SMTP connection errors"""
    request_id = getattr(request.state, "request_id", None)
    logger.error(f"SMTP connection error: {exc}", extra={"request_id": request_id})

    return JSONResponse(
        status_code=status.HTTP_502_BAD_GATEWAY,
        content=ErrorResponse(
            error="smtp_connection_error",
            message="Failed to connect to email server",
            request_id=request_id,
        ).model_dump(),
    )


@app.exception_handler(EmailSendError)
async def email_send_handler(request: Request, exc: EmailSendError):
    """Handle email sending errors"""
    request_id = getattr(request.state, "request_id", None)
    logger.error(f"Email send error: {exc}", extra={"request_id": request_id})

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="email_send_error",
            message=str(exc),
            request_id=request_id,
        ).model_dump(),
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all uncaught exceptions"""
    request_id = getattr(request.state, "request_id", None)
    logger.error(f"Unhandled exception: {exc}", extra={"request_id": request_id}, exc_info=True)

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="internal_server_error",
            message="An unexpected error occurred",
            request_id=request_id,
        ).model_dump(),
    )


# Routes
@app.get("/", tags=["General"])
async def root():
    """Root endpoint with service information"""
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "environment": settings.environment,
        "docs": "/docs",
    }


@app.get("/health", response_model=HealthResponse, tags=["Monitoring"])
async def health_check():
    """
    Comprehensive health check endpoint

    Checks:
    - Service is running
    - Email configuration is valid
    - SMTP server is reachable (optional)
    """
    email_service = get_email_service()
    email_configured = bool(settings.email_password)

    # Optional: Check SMTP connectivity (can be slow)
    smtp_reachable = None
    if email_configured:
        try:
            smtp_reachable = email_service.check_smtp_connection()
        except Exception as e:
            logger.warning(f"SMTP health check failed: {e}")
            smtp_reachable = False

    return HealthResponse(
        status="healthy",
        version=settings.app_version,
        environment=settings.environment,
        email_configured=email_configured,
        smtp_reachable=smtp_reachable,
    )


@app.post(
    f"{settings.api_prefix}/send-email",
    response_model=EmailResponse,
    status_code=status.HTTP_200_OK,
    tags=["Email"],
    summary="Send confirmation email",
    response_description="Email sent successfully",
)
async def send_email(request: Request, email_request: EmailRequest):
    """
    Send a confirmation email to a user

    This endpoint sends a professionally formatted HTML email using the configured template.

    **Features:**
    - Automatic retry on transient failures (up to 3 attempts)
    - Email template validation
    - Request tracking with unique ID
    - Structured logging

    **Request Body:**
    - **user_name**: Full name of the recipient
    - **user_email**: Valid email address
    - **meeting_time**: Human-readable meeting time description

    **Rate Limiting:**
    - Maximum 10 requests per 60 seconds per IP address
    """
    request_id = getattr(request.state, "request_id", None)

    logger.info(
        f"Received email request for {email_request.user_email}",
        extra={"request_id": request_id, "user_email": email_request.user_email},
    )

    try:
        email_service = get_email_service()
        result = await email_service.send_email_async(
            user_name=email_request.user_name,
            user_email=email_request.user_email,
            meeting_time=email_request.meeting_time,
            request_id=request_id,
        )

        return EmailResponse(
            success=result["success"],
            message=result["message"],
            recipient=result["recipient"],
            request_id=request_id,
        )

    except (EmailTemplateNotFoundError, SMTPConnectionError, EmailSendError):
        # These are handled by exception handlers
        raise

    except Exception as e:
        logger.error(
            f"Unexpected error processing email request: {e}",
            extra={"request_id": request_id},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while sending the email",
        )


@app.get("/metrics", tags=["Monitoring"])
async def metrics():
    """
    Basic metrics endpoint

    In production, integrate with Prometheus or similar monitoring tools
    """
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
