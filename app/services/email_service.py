"""
Email service for sending notifications to students about registration status updates.
"""

import os
from email.mime.multipart import MimeMultipart
from email.mime.text import MimeText
from typing import List, Optional

import aiosmtplib
from jinja2 import Environment, FileSystemLoader

from app.core.logging_config import get_logger
from app.models.review import RegistrationStatus
from app.schemas.email_notification import EmailSendResult

logger = get_logger(__name__)


class EmailService:
    """Service for sending emails to students about registration updates."""

    def __init__(self):
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_username = os.getenv("SMTP_USERNAME")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        if not self.smtp_username:
            raise ValueError("Missing required SMTP_USERNAME environment variable.")
        if not self.smtp_password:
            raise ValueError("Missing required SMTP_PASSWORD environment variable.")
        self.from_email = os.getenv("FROM_EMAIL", self.smtp_username)
        self.frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")

        template_dir = os.path.join(
            os.path.dirname(__file__), "..", "templates", "emails"
        )
        os.makedirs(template_dir, exist_ok=True)
        self.jinja_env = Environment(loader=FileSystemLoader(template_dir))

    async def send_registration_status_email(
        self,
        student_email: str,
        student_name: str,
        notice_title: str,
        status: RegistrationStatus,
        ivs_score: Optional[float] = None,
        requested_documents: Optional[List[str]] = None,
    ) -> EmailSendResult:
        """
        Send email notification about registration status update.

        Args:
            student_email: Student's email address
            student_name: Student's full name
            notice_title: Title of the notice/edital
            status: Registration status (APPROVED, REJECTED, APPEAL)
            ivs_score: IVS score for approved registrations
            requested_documents: List of requested documents for appeals

        Returns:
            EmailSendResult: Result schema containing success status and message
        """
        try:
            # Choose template based on status
            if status == RegistrationStatus.APPROVED:
                template_name = "registration_approved.html"
                subject = f"✅ Inscrição Aprovada - {notice_title}"
            elif status == RegistrationStatus.REJECTED:
                template_name = "registration_rejected.html"
                subject = f"❌ Inscrição Rejeitada - {notice_title}"
            elif status == RegistrationStatus.APPEAL:
                template_name = "registration_appeal.html"
                subject = f"⚠️ Documentos Solicitados - {notice_title}"
            else:
                logger.warning(f"Unknown status for email: {status}")
                return EmailSendResult(
                    success=False,
                    message=f"Unknown status: {status}",
                    email_address=student_email,
                )

            template = self.jinja_env.get_template(template_name)
            html_content = template.render(
                student_name=student_name,
                notice_title=notice_title,
                ivs_score=ivs_score,
                requested_documents=requested_documents or [],
                home_url=f"{self.frontend_url}/",
            )

            message = MimeMultipart("alternative")
            message["Subject"] = subject
            message["From"] = self.from_email
            message["To"] = student_email

            html_part = MimeText(html_content, "html", "utf-8")
            message.attach(html_part)

            await aiosmtplib.send(
                message,
                hostname=self.smtp_server,
                port=self.smtp_port,
                start_tls=True,
                username=self.smtp_username,
                password=self.smtp_password,
            )

            logger.info(
                f"Email sent successfully to {student_email} for status {status}"
            )
            return EmailSendResult(
                success=True,
                message="Email sent successfully",
                email_address=student_email,
            )

        except Exception as e:
            error_message = f"Failed to send email to {student_email}: {str(e)}"
            logger.error(error_message)
            return EmailSendResult(
                success=False, message=error_message, email_address=student_email
            )


email_service = EmailService()
