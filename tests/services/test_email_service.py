import pytest
from unittest.mock import AsyncMock, patch
from app.services.email_service import EmailService
from app.models.review import RegistrationStatus


@pytest.fixture(autouse=True)
def mock_env_vars(monkeypatch):
    monkeypatch.setenv("SMTP_SERVER", "smtp.test.com")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_USERNAME", "testuser")
    monkeypatch.setenv("SMTP_PASSWORD", "testpass")
    monkeypatch.setenv("FROM_EMAIL", "from@test.com")
    monkeypatch.setenv("FRONTEND_URL", "http://localhost:3000")


@pytest.mark.asyncio
@patch("aiosmtplib.send", new_callable=AsyncMock)
async def test_send_registration_status_email_approved(mock_send):
    """
    Test sending an 'approved' registration status email.
    """
    email_service = EmailService()
    result = await email_service.send_registration_status_email(
        student_email="student@test.com",
        student_name="Test Student",
        notice_title="Test Notice",
        status=RegistrationStatus.APPROVED,
        ivs_score=80.5,
    )

    assert result.success is True
    assert result.email_address == "student@test.com"
    mock_send.assert_called_once()
    message = mock_send.call_args[0][0]
    assert message["To"] == "student@test.com"
    assert message["From"] == "from@test.com"
    assert message["Subject"] == " Inscrição Aprovada - Test Notice"

@pytest.mark.asyncio
@patch("aiosmtplib.send", new_callable=AsyncMock)
async def test_send_registration_status_email_rejected(mock_send):
    """
    Test sending a 'rejected' registration status email.
    """
    email_service = EmailService()
    result = await email_service.send_registration_status_email(
        student_email="student@test.com",
        student_name="Test Student",
        notice_title="Test Notice",
        status=RegistrationStatus.REJECTED,
    )

    assert result.success is True
    assert result.email_address == "student@test.com"
    mock_send.assert_called_once()
    message = mock_send.call_args[0][0]
    assert message["To"] == "student@test.com"
    assert message["Subject"] == " Inscrição Rejeitada - Test Notice"

@pytest.mark.asyncio
@patch("aiosmtplib.send", new_callable=AsyncMock)
async def test_send_registration_status_email_appeal(mock_send):
    """
    Test sending an 'appeal' registration status email.
    """
    email_service = EmailService()
    result = await email_service.send_registration_status_email(
        student_email="student@test.com",
        student_name="Test Student",
        notice_title="Test Notice",
        status=RegistrationStatus.APPEAL,
        requested_documents=["doc1", "doc2"],
    )

    assert result.success is True
    assert result.email_address == "student@test.com"
    mock_send.assert_called_once()
    message = mock_send.call_args[0][0]
    assert message["To"] == "student@test.com"
    assert message["Subject"] == " Documentos Solicitados - Test Notice"

@pytest.mark.asyncio
async def test_send_email_unknown_status():
    """
    Test that sending an email with an unknown status fails gracefully.
    """
    email_service = EmailService()
    result = await email_service.send_registration_status_email(
        student_email="student@test.com",
        student_name="Test Student",
        notice_title="Test Notice",
        status="UNKNOWN_STATUS",
    )

    assert result.success is False
    assert "Unknown status" in result.message


@pytest.mark.asyncio
@patch("aiosmtplib.send", new_callable=AsyncMock, side_effect=Exception("SMTP Error"))
async def test_send_email_smtp_error(mock_send):
    """
    Test handling of an SMTP error during email sending.
    """
    email_service = EmailService()
    result = await email_service.send_registration_status_email(
        student_email="student@test.com",
        student_name="Test Student",
        notice_title="Test Notice",
        status=RegistrationStatus.APPROVED,
    )

    assert result.success is False
    assert "Failed to send email" in result.message
    assert "SMTP Error" in result.message
