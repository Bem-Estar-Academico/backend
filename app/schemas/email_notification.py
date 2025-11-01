"""
Schemas for email notification data.
"""

from typing import List, Optional

from pydantic import BaseModel, EmailStr

from app.models.review import RegistrationStatus


class EmailNotificationData(BaseModel):
    """
    Schema for email notification data extracted from review and related models.
    """

    student_email: EmailStr
    student_name: str
    notice_title: str
    status: RegistrationStatus
    ivs_score: Optional[float] = None
    requested_documents: Optional[List[str]] = None

    class Config:
        """Pydantic configuration."""

        from_attributes = True


class EmailSendResult(BaseModel):
    """
    Schema for email sending result.
    """

    success: bool
    message: str
    email_address: Optional[str] = None
