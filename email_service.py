"""
Email service with retry logic and async support
"""
import smtplib
import asyncio
import datetime
import uuid
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from typing import Dict, Optional, Tuple
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
import dateparser
import pytz

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

    def _parse_meeting_time(self, raw_time_string: str) -> Tuple[Optional[datetime.datetime], Optional[datetime.datetime]]:
        """
        Converts human string (e.g., "Nov 29th 5pm PST") into a strict UTC datetime object.

        Args:
            raw_time_string: Human-readable time string

        Returns:
            Tuple of (start_time_utc, end_time_utc) or (None, None) if parsing fails
        """
        settings = {
            'TIMEZONE': 'US/Pacific',
            'RETURN_AS_TIMEZONE_AWARE': True
        }

        dt = dateparser.parse(raw_time_string, settings=settings)

        if not dt:
            logger.error(f"Could not parse time: {raw_time_string}")
            return None, None

        # Calculate End Time (15 minute meeting)
        dt_end = dt + datetime.timedelta(minutes=15)

        # Convert both to UTC (Computer Time) for the ICS file
        dt_start_utc = dt.astimezone(pytz.utc)
        dt_end_utc = dt_end.astimezone(pytz.utc)

        return dt_start_utc, dt_end_utc

    def _generate_ics_content(self, user_name: str, user_email: str, start_utc: datetime.datetime, end_utc: datetime.datetime) -> str:
        """
        Creates the text content for the .ics calendar file.

        Args:
            user_name: Name of the user
            user_email: Email address of the user
            start_utc: Meeting start time in UTC
            end_utc: Meeting end time in UTC

        Returns:
            ICS file content as string
        """
        # Formatting time as YYYYMMDDTHHMMSSZ
        fmt = "%Y%m%dT%H%M%SZ"
        start_str = start_utc.strftime(fmt)
        end_str = end_utc.strftime(fmt)
        now_str = datetime.datetime.now(datetime.timezone.utc).strftime(fmt)
        unique_id = str(uuid.uuid4())

        meet_link = self.settings.permanent_meeting_link

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
DESCRIPTION:Hi {user_name},\\n\\nThis is the technical discovery call you booked with Lena.\\n\\nHost: Chitraksha ({self.settings.host_email})\\n\\nJoin the Google Meet here: {meet_link}
LOCATION:{meet_link}
ORGANIZER;CN=Ask Lena AI:mailto:{self.settings.sender_email}
ATTENDEE;ROLE=REQ-PARTICIPANT;RSVP=TRUE;CN={user_name}:mailto:{user_email}
ATTENDEE;ROLE=REQ-PARTICIPANT;RSVP=TRUE;CN=Chitraksha:mailto:{self.settings.host_email}
STATUS:CONFIRMED
END:VEVENT
END:VCALENDAR"""

        return ics_body

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
        personalized = personalized.replace("{GOOGLE_MEET_LINK_HERE}", self.settings.permanent_meeting_link)
        return personalized

    def _create_message(
        self, user_name: str, user_email: str, meeting_time: str, personalized_html: str, ics_content: Optional[str] = None
    ) -> MIMEMultipart:
        """
        Create email message

        Args:
            user_name: Name of the user
            user_email: Email address
            meeting_time: Meeting time string
            personalized_html: Personalized HTML content
            ics_content: Optional ICS calendar content

        Returns:
            MIME message object
        """
        msg = MIMEMultipart("mixed")
        msg["Subject"] = f"Invitation: Tech Discovery Call with {user_name}"
        msg["From"] = f"{self.settings.sender_name} <{self.settings.sender_email}>"
        msg["To"] = user_email
        msg["Cc"] = self.settings.host_email

        # Create HTML part
        msg_html = MIMEMultipart("alternative")
        msg_html.attach(MIMEText(personalized_html, "html"))
        msg.attach(msg_html)

        # Attach ICS file if provided
        if ics_content:
            part_ics = MIMEBase("text", "calendar", method="REQUEST", name="invite.ics")
            part_ics.set_payload(ics_content)
            encoders.encode_base64(part_ics)
            part_ics.add_header('Content-Description', 'Meeting Invitation')
            part_ics.add_header('Content-class', 'urn:content-classes:calendarmessage')
            msg.attach(part_ics)

        return msg

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=10),
        retry=retry_if_exception_type((smtplib.SMTPException, ConnectionError)),
        reraise=True,
    )
    def _send_via_smtp(self, msg: MIMEMultipart, recipients: list) -> None:
        """
        Send email via SMTP with retry logic

        Args:
            msg: Email message
            recipients: List of recipient email addresses

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
            server.sendmail(self.settings.sender_email, recipients, msg.as_string())
            server.quit()
            logger.info(f"Email sent successfully to {', '.join(recipients)}")

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
            # Parse meeting time
            start_utc, end_utc = self._parse_meeting_time(meeting_time)
            if not start_utc:
                raise EmailSendError(f"Could not parse meeting time: {meeting_time}")

            # Personalize template
            personalized_html = self._personalize_template(user_name, meeting_time)

            # Generate ICS content
            ics_content = self._generate_ics_content(user_name, user_email, start_utc, end_utc)

            # Create message with ICS attachment
            msg = self._create_message(user_name, user_email, meeting_time, personalized_html, ics_content)

            # Prepare recipients list (user and host)
            recipients = [user_email, self.settings.host_email]

            # Send email in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._send_via_smtp, msg, recipients)

            result = {
                "success": True,
                "message": f"Email successfully sent to {user_email} (and copied {self.settings.host_email})",
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
