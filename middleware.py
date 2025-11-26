"""
Custom middleware for request tracking and rate limiting
"""
import time
import uuid
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Callable, Dict
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from config import get_settings
from logger import logger
from exceptions import RateLimitExceeded


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware to add unique request ID to each request"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add request ID to request state and response headers"""
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # Add request ID to logger context
        logger.info(
            f"Incoming request: {request.method} {request.url.path}",
            extra={"request_id": request_id}
        )

        start_time = time.time()

        response = await call_next(request)

        # Calculate request duration
        duration = time.time() - start_time

        # Add headers to response
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = f"{duration:.3f}s"

        logger.info(
            f"Request completed: {request.method} {request.url.path} - "
            f"Status: {response.status_code} - Duration: {duration:.3f}s",
            extra={"request_id": request_id}
        )

        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware for rate limiting requests per IP"""

    def __init__(self, app):
        super().__init__(app)
        self.settings = get_settings()
        self.requests: Dict[str, list] = defaultdict(list)

    def _clean_old_requests(self, ip: str, current_time: datetime) -> None:
        """Remove requests outside the time window"""
        cutoff_time = current_time - timedelta(seconds=self.settings.rate_limit_window)
        self.requests[ip] = [
            req_time for req_time in self.requests[ip] if req_time > cutoff_time
        ]

    def _is_rate_limited(self, ip: str) -> bool:
        """Check if IP has exceeded rate limit"""
        if not self.settings.rate_limit_enabled:
            return False

        current_time = datetime.utcnow()
        self._clean_old_requests(ip, current_time)

        request_count = len(self.requests[ip])

        if request_count >= self.settings.rate_limit_requests:
            logger.warning(
                f"Rate limit exceeded for IP: {ip}",
                extra={"ip": ip, "request_count": request_count}
            )
            return True

        self.requests[ip].append(current_time)
        return False

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Check rate limit before processing request"""
        # Skip rate limiting for health check endpoints
        if request.url.path in ["/health", "/", "/docs", "/openapi.json"]:
            return await call_next(request)

        # Get client IP
        client_ip = request.client.host if request.client else "unknown"

        # Check rate limit
        if self._is_rate_limited(client_ip):
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "rate_limit_exceeded",
                    "message": f"Rate limit exceeded. Maximum {self.settings.rate_limit_requests} "
                    f"requests per {self.settings.rate_limit_window} seconds.",
                    "retry_after": self.settings.rate_limit_window,
                },
            )

        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add security headers to response"""
        response = await call_next(request)

        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        return response
