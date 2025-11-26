"""
Custom exceptions for the application
"""


class EmailServiceError(Exception):
    """Base exception for email service errors"""
    pass


class EmailTemplateNotFoundError(EmailServiceError):
    """Raised when email template file is not found"""
    pass


class EmailSendError(EmailServiceError):
    """Raised when email sending fails"""
    pass


class SMTPConnectionError(EmailServiceError):
    """Raised when SMTP connection fails"""
    pass


class ConfigurationError(Exception):
    """Raised when configuration is invalid"""
    pass


class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded"""
    pass
