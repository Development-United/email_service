"""
Email service with retry logic and async support
"""
import smtplib
import asyncio
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Dict, Optional
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from config import get_settings
from exceptions import (
    EmailTemplateNotFoundError,
    EmailSendError,
    SMTPConnectionError,
)
from logger import logger


class EmailService:
    """Service for sending emails with retry logic"""

    def __init__(self):
        """Initialize email service"""
        self.settings = get_settings()
        self._template_cache: Optional[str] = None
        self._validate_template()

    def _validate_template(self) -> None:
        """Validate that email template exists on startup"""
        template_path = Path(self.settings.email_template_path)
        if not template_path.exists():
            logger.error(f"Email template not found at {template_path}")
            raise EmailTemplateNotFoundError(
                f"Email template not found: {self.settings.email_template_path}"
            )
        logger.info(f"Email template validated: {template_path}")

    def _load_template(self) -> str:
        """
        Load and cache email template

        Returns:
            Template content as string

        Raises:
            EmailTemplateNotFoundError: If template file not found
        """
        if self._template_cache is not None:
            return self._template_cache

        try:
            with open(self.settings.email_template_path, "r", encoding="utf-8") as f:
                self._template_cache = f.read()
                logger.debug("Email template loaded and cached")
                return self._template_cache
        except FileNotFoundError:
            logger.error(f"Email template not found: {self.settings.email_template_path}")
            raise EmailTemplateNotFoundError(
                f"Email template not found: {self.settings.email_template_path}"
            )

    def _personalize_template(self, user_name: str, meeting_time: str) -> str:
        """
        Personalize email template with user data

        Args:
            user_name: Name of the user
            meeting_time: Meeting time string

        Returns:
            Personalized HTML content
        """
        html_content = self._load_template()
        personalized = html_content.replace("{user_name}", user_name)
        personalized = personalized.replace("{meeting_time}", meeting_time)
        return personalized

    def _create_message(
        self, user_name: str, user_email: str, meeting_time: str, personalized_html: str
    ) -> MIMEMultipart:
        """
        Create email message

        Args:
            user_name: Name of the user
            user_email: Email address
            meeting_time: Meeting time string
            personalized_html: Personalized HTML content

        Returns:
            MIME message object
        """
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"Confirmation: Tech Discovery Call with {user_name}"
        msg["From"] = f"{self.settings.sender_name} <{self.settings.sender_email}>"
        msg["To"] = user_email

        # Plain text fallback
        text_content = (
            f"Hi {user_name}, your meeting is confirmed for {meeting_time}. "
            f"A calendar invitation has been sent separately."
        )
        text_part = MIMEText(text_content, "plain")
        html_part = MIMEText(personalized_html, "html")

        msg.attach(text_part)
        msg.attach(html_part)

        return msg

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=10),
        retry=retry_if_exception_type((smtplib.SMTPException, ConnectionError)),
        reraise=True,
    )
    def _send_via_smtp(self, msg: MIMEMultipart, recipient: str) -> None:
        """
        Send email via SMTP with retry logic

        Args:
            msg: Email message
            recipient: Recipient email address

        Raises:
            SMTPConnectionError: If SMTP connection fails
            EmailSendError: If email sending fails
        """
        try:
            logger.info(f"Connecting to SMTP server: {self.settings.smtp_server}:{self.settings.smtp_port}")
            server = smtplib.SMTP(
                self.settings.smtp_server,
                self.settings.smtp_port,
                timeout=self.settings.email_timeout,
            )
            server.starttls()
            server.login(self.settings.sender_email, self.settings.email_password)
            server.sendmail(self.settings.sender_email, recipient, msg.as_string())
            server.quit()
            logger.info(f"Email sent successfully to {recipient}")

        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP authentication failed: {e}")
            raise SMTPConnectionError(f"SMTP authentication failed: {e}")

        except smtplib.SMTPException as e:
            logger.error(f"SMTP error occurred: {e}")
            raise EmailSendError(f"Failed to send email via SMTP: {e}")

        except Exception as e:
            logger.error(f"Unexpected error sending email: {e}")
            raise EmailSendError(f"Unexpected error: {e}")

    async def send_email_async(
        self, user_name: str, user_email: str, meeting_time: str, request_id: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Send email asynchronously

        Args:
            user_name: Name of the user
            user_email: Email address
            meeting_time: Meeting time string
            request_id: Optional request ID for tracking

        Returns:
            Dict with success status and message

        Raises:
            EmailTemplateNotFoundError: If template not found
            EmailSendError: If sending fails
        """
        extra = {"request_id": request_id, "user_email": user_email} if request_id else {"user_email": user_email}
        logger.info(f"Processing email request for {user_email}", extra=extra)

        try:
            # Personalize template
            personalized_html = self._personalize_template(user_name, meeting_time)

            # Create message
            msg = self._create_message(user_name, user_email, meeting_time, personalized_html)

            # Send email in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._send_via_smtp, msg, user_email)

            result = {
                "success": True,
                "message": f"Email successfully sent to {user_email}",
                "recipient": user_email,
            }
            logger.info(f"Email request completed successfully for {user_email}", extra=extra)
            return result

        except (EmailTemplateNotFoundError, SMTPConnectionError, EmailSendError) as e:
            logger.error(f"Email service error: {e}", extra=extra)
            raise

        except Exception as e:
            logger.error(f"Unexpected error in email service: {e}", extra=extra, exc_info=True)
            raise EmailSendError(f"Unexpected error: {e}")

    def check_smtp_connection(self) -> bool:
        """
        Check if SMTP server is reachable

        Returns:
            True if connection successful, False otherwise
        """
        try:
            server = smtplib.SMTP(
                self.settings.smtp_server,
                self.settings.smtp_port,
                timeout=5,
            )
            server.quit()
            logger.debug("SMTP server is reachable")
            return True
        except Exception as e:
            logger.warning(f"SMTP server not reachable: {e}")
            return False


# Singleton instance
_email_service: Optional[EmailService] = None


def get_email_service() -> EmailService:
    """Get or create email service instance"""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service
