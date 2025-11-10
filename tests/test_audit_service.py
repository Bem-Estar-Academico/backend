"""
Tests for audit service functionality.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import Request

from app.models.audit import AuditAction, AuditEntityType, AuditLog
from app.services.audit_service import AuditService


class TestAuditService:
    """Test cases for AuditService."""

    @pytest.mark.asyncio
    async def test_create_audit_log_success(self):
        """Test successful audit log creation."""
        # Arrange
        mock_db = AsyncMock()
        mock_audit_log = AuditLog(
            id=1,
            action=AuditAction.NOTICE_CREATED,
            entity_type=AuditEntityType.NOTICE,
            entity_id=123,
            user_id=456,
            description="Test notice created",
            metadata={"test": "data"},
            created_at=datetime.now(timezone.utc),
        )
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        # Act
        result = await AuditService.create_audit_log(
            db=mock_db,
            action=AuditAction.NOTICE_CREATED,
            entity_type=AuditEntityType.NOTICE,
            entity_id=123,
            user_id=456,
            description="Test notice created",
            metadata={"test": "data"},
        )

        # Assert
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_audit_log_invalid_entity_id(self):
        """Test audit log creation with invalid entity_id."""
        # Arrange
        mock_db = AsyncMock()

        # Act & Assert
        with pytest.raises(ValueError, match="entity_id must be positive"):
            await AuditService.create_audit_log(
                db=mock_db,
                action=AuditAction.NOTICE_CREATED,
                entity_type=AuditEntityType.NOTICE,
                entity_id=0,  # Invalid
                user_id=456,
                description="Test notice created",
            )

    @pytest.mark.asyncio
    async def test_create_audit_log_invalid_user_id(self):
        """Test audit log creation with invalid user_id."""
        # Arrange
        mock_db = AsyncMock()

        # Act & Assert
        with pytest.raises(ValueError, match="user_id must be positive"):
            await AuditService.create_audit_log(
                db=mock_db,
                action=AuditAction.NOTICE_CREATED,
                entity_type=AuditEntityType.NOTICE,
                entity_id=123,
                user_id=-1,  # Invalid
                description="Test notice created",
            )

    @pytest.mark.asyncio
    async def test_create_audit_log_empty_description(self):
        """Test audit log creation with empty description."""
        # Arrange
        mock_db = AsyncMock()

        # Act & Assert
        with pytest.raises(ValueError, match="description cannot be empty"):
            await AuditService.create_audit_log(
                db=mock_db,
                action=AuditAction.NOTICE_CREATED,
                entity_type=AuditEntityType.NOTICE,
                entity_id=123,
                user_id=456,
                description="   ",  # Empty/whitespace
            )

    @pytest.mark.asyncio
    async def test_create_audit_log_database_error(self):
        """Test audit log creation with database error."""
        # Arrange
        mock_db = AsyncMock()
        mock_db.commit.side_effect = Exception("Database error")
        mock_db.rollback = AsyncMock()

        # Act & Assert
        with pytest.raises(Exception, match="Database error"):
            await AuditService.create_audit_log(
                db=mock_db,
                action=AuditAction.NOTICE_CREATED,
                entity_type=AuditEntityType.NOTICE,
                entity_id=123,
                user_id=456,
                description="Test notice created",
            )

        mock_db.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_audit_logs_with_filters(self):
        """Test getting audit logs with various filters."""
        # Arrange
        mock_db = AsyncMock()
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        # Act
        result = await AuditService.get_audit_logs(
            db=mock_db,
            skip=10,
            limit=50,
            action_filter=AuditAction.NOTICE_CREATED,
            entity_type_filter=AuditEntityType.NOTICE,
            entity_id_filter=123,
            user_id_filter=456,
        )

        # Assert
        assert result == []
        mock_db.execute.assert_called_once()

    def test_extract_client_info_with_forwarded_for(self):
        """Test extracting client info with X-Forwarded-For header."""
        # Arrange
        mock_request = MagicMock(spec=Request)
        mock_request.headers = {
            "X-Forwarded-For": "192.168.1.1, 10.0.0.1",
            "User-Agent": "Mozilla/5.0 (Test Browser)",
        }

        # Act
        ip, user_agent = AuditService.extract_client_info(mock_request)

        # Assert
        assert ip == "192.168.1.1"
        assert user_agent == "Mozilla/5.0 (Test Browser)"

    def test_extract_client_info_with_real_ip(self):
        """Test extracting client info with X-Real-IP header."""
        # Arrange
        mock_request = MagicMock(spec=Request)
        mock_request.headers = {
            "X-Real-IP": "192.168.1.100",
            "User-Agent": "Test Agent",
        }

        # Act
        ip, user_agent = AuditService.extract_client_info(mock_request)

        # Assert
        assert ip == "192.168.1.100"
        assert user_agent == "Test Agent"

    def test_extract_client_info_no_request(self):
        """Test extracting client info without request."""
        # Act
        ip, user_agent = AuditService.extract_client_info(None)

        # Assert
        assert ip is None
        assert user_agent is None

    def test_extract_client_info_fallback_to_client_host(self):
        """Test extracting client info fallback to client.host."""
        # Arrange
        mock_client = MagicMock()
        mock_client.host = "127.0.0.1"
        mock_request = MagicMock(spec=Request)
        mock_request.headers = {"User-Agent": "Test Agent"}
        mock_request.client = mock_client

        # Act
        ip, user_agent = AuditService.extract_client_info(mock_request)

        # Assert
        assert ip == "127.0.0.1"
        assert user_agent == "Test Agent"
