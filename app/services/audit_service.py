"""
Service for managing audit logs.
"""

from typing import Any, Dict, List, Optional

from fastapi import Request
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging_config import get_logger
from app.models.audit import AuditAction, AuditEntityType, AuditLog

logger = get_logger(__name__)


class AuditService:
    """Service for managing audit logs."""

    @staticmethod
    def extract_client_info(
        request: Optional[Request] = None,
    ) -> tuple[Optional[str], Optional[str]]:
        """
        Extract client IP address and User-Agent from request.

        Args:
            request: FastAPI request object

        Returns:
            Tuple of (ip_address, user_agent)
        """
        if not request:
            return None, None

        ip_address = request.headers.get("X-Forwarded-For")
        if ip_address:
            ip_address = ip_address.split(",")[0].strip()
        else:
            ip_address = request.headers.get("X-Real-IP")
            if not ip_address:
                ip_address = request.client.host if request.client else None

        user_agent = request.headers.get("User-Agent")

        return ip_address, user_agent

    @staticmethod
    async def create_audit_log(
        db: AsyncSession,
        action: AuditAction,
        entity_type: AuditEntityType,
        entity_id: int,
        user_id: int,
        description: str,
        metadata: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        """
        Create a new audit log entry.

        Args:
            db: Database session
            action: The action performed
            entity_type: Type of entity affected
            entity_id: ID of the entity affected
            user_id: ID of the user who performed the action
            description: Human-readable description
            metadata: Additional context data
            ip_address: IP address of the user
            user_agent: User agent string of the client

        Returns:
            Created audit log entry

        Raises:
            ValueError: If required parameters are invalid
        """
        try:
            if entity_id <= 0:
                raise ValueError("entity_id must be positive")
            if user_id <= 0:
                raise ValueError("user_id must be positive")
            if not description.strip():
                raise ValueError("description cannot be empty")

            audit_log = AuditLog(
                action=action.value,
                entity_type=entity_type.value,
                entity_id=entity_id,
                user_id=user_id,
                description=description.strip(),
                meta_data=metadata or {},
                ip_address=ip_address,
                user_agent=user_agent,
            )

            db.add(audit_log)
            await db.commit()
            await db.refresh(audit_log)

            logger.info(
                f"Audit log created: {action.value} on {entity_type.value} #{entity_id} by user #{user_id}"
            )

            return audit_log

        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to create audit log: {str(e)}")
            raise

    @staticmethod
    async def get_audit_logs(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        action_filter: Optional[AuditAction] = None,
        entity_type_filter: Optional[AuditEntityType] = None,
        entity_id_filter: Optional[int] = None,
        user_id_filter: Optional[int] = None,
    ) -> List[AuditLog]:
        """
        Get audit logs with optional filters.

        Args:
            db: Database session
            skip: Number of records to skip
            limit: Maximum number of records to return
            action_filter: Filter by action type
            entity_type_filter: Filter by entity type
            entity_id_filter: Filter by entity ID
            user_id_filter: Filter by user ID

        Returns:
            List of audit log entries
        """
        try:
            query = (
                select(AuditLog)
                .options(selectinload(AuditLog.user))
                .order_by(desc(AuditLog.created_at))
                .offset(skip)
                .limit(limit)
            )

            if action_filter:
                query = query.where(AuditLog.action == action_filter.value)

            if entity_type_filter:
                query = query.where(AuditLog.entity_type == entity_type_filter.value)

            if entity_id_filter:
                query = query.where(AuditLog.entity_id == entity_id_filter)

            if user_id_filter:
                query = query.where(AuditLog.user_id == user_id_filter)

            result = await db.execute(query)
            return list(result.scalars().all())

        except Exception as e:
            logger.error(f"Failed to get audit logs: {str(e)}")
            raise

    @staticmethod
    async def get_audit_logs_for_entity(
        db: AsyncSession, entity_type: AuditEntityType, entity_id: int, limit: int = 50
    ) -> List[AuditLog]:
        """
        Get audit logs for a specific entity.

        Args:
            db: Database session
            entity_type: Type of entity
            entity_id: ID of the entity
            limit: Maximum number of records to return

        Returns:
            List of audit log entries for the entity
        """
        query = (
            select(AuditLog)
            .options(selectinload(AuditLog.user))
            .where(AuditLog.entity_type == entity_type.value)
            .where(AuditLog.entity_id == entity_id)
            .order_by(desc(AuditLog.created_at))
            .limit(limit)
        )

        result = await db.execute(query)
        return list(result.scalars().all())


async def audit_notice_created(
    db: AsyncSession,
    notice_id: int,
    user_id: int,
    notice_title: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
):
    """Audit when a notice is created."""
    await AuditService.create_audit_log(
        db=db,
        action=AuditAction.NOTICE_CREATED,
        entity_type=AuditEntityType.NOTICE,
        entity_id=notice_id,
        user_id=user_id,
        description=f"Edital '{notice_title}' criado",
        metadata={"notice_title": notice_title},
        ip_address=ip_address,
        user_agent=user_agent,
    )


async def audit_notice_updated(
    db: AsyncSession,
    notice_id: int,
    user_id: int,
    notice_title: str,
    updated_fields: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
):
    """Audit when a notice is updated."""
    await AuditService.create_audit_log(
        db=db,
        action=AuditAction.NOTICE_UPDATED,
        entity_type=AuditEntityType.NOTICE,
        entity_id=notice_id,
        user_id=user_id,
        description=f"Edital '{notice_title}' atualizado",
        metadata={"notice_title": notice_title, "updated_fields": updated_fields or {}},
        ip_address=ip_address,
        user_agent=user_agent,
    )


async def audit_notice_deleted(
    db: AsyncSession,
    notice_id: int,
    user_id: int,
    notice_title: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
):
    """Audit when a notice is deleted."""
    await AuditService.create_audit_log(
        db=db,
        action=AuditAction.NOTICE_DELETED,
        entity_type=AuditEntityType.NOTICE,
        entity_id=notice_id,
        user_id=user_id,
        description=f"Edital '{notice_title}' removido",
        metadata={"notice_title": notice_title},
        ip_address=ip_address,
        user_agent=user_agent,
    )


async def audit_review_status_changed(
    db: AsyncSession,
    review_id: int,
    user_id: int,
    old_status: str,
    new_status: str,
    student_name: str,
    metadata: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
):
    """Audit when a review status changes."""
    action_map = {
        "APPROVED": AuditAction.REVIEW_APPROVED,
        "REJECTED": AuditAction.REVIEW_REJECTED,
        "APPEAL": AuditAction.APPEAL_SUBMITTED,
    }

    action = action_map.get(new_status, AuditAction.REVIEW_UPDATED)
    description_map = {
        "APPROVED": "Inscrição aprovada na análise",
        "REJECTED": "Inscrição rejeitada na análise",
        "APPEAL": "Documentos adicionais solicitados",
    }

    description = description_map.get(
        new_status, f"Status alterado de {old_status} para {new_status}"
    )

    audit_metadata = {
        "student_name": student_name,
        "old_status": old_status,
        "new_status": new_status,
        **(metadata or {}),
    }

    await AuditService.create_audit_log(
        db=db,
        action=action,
        entity_type=AuditEntityType.REVIEW,
        entity_id=review_id,
        user_id=user_id,
        description=description,
        metadata=audit_metadata,
        ip_address=ip_address,
        user_agent=user_agent,
    )


async def audit_registration_submitted(
    db: AsyncSession,
    registration_id: int,
    user_id: int,
    notice_title: str,
    student_name: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
):
    """Audit when a student registration is submitted."""
    await AuditService.create_audit_log(
        db=db,
        action=AuditAction.REGISTRATION_SUBMITTED,
        entity_type=AuditEntityType.REGISTRATION,
        entity_id=registration_id,
        user_id=user_id,
        description=f"Inscrição submetida no edital '{notice_title}'",
        metadata={"notice_title": notice_title, "student_name": student_name},
        ip_address=ip_address,
        user_agent=user_agent,
    )


async def audit_document_uploaded(
    db: AsyncSession,
    document_id: int,
    user_id: int,
    document_name: str,
    entity_type: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
):
    """Audit when a document is uploaded."""
    await AuditService.create_audit_log(
        db=db,
        action=AuditAction.DOCUMENT_UPLOADED,
        entity_type=AuditEntityType.DOCUMENT,
        entity_id=document_id,
        user_id=user_id,
        description=f"Documento '{document_name}' enviado",
        metadata={"document_name": document_name, "entity_type": entity_type},
        ip_address=ip_address,
        user_agent=user_agent,
    )


async def audit_document_deleted(
    db: AsyncSession,
    document_id: int,
    user_id: int,
    document_name: str,
    entity_type: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
):
    """Audit when a document is deleted."""
    await AuditService.create_audit_log(
        db=db,
        action=AuditAction.DOCUMENT_DELETED,
        entity_type=AuditEntityType.DOCUMENT,
        entity_id=document_id,
        user_id=user_id,
        description=f"Documento '{document_name}' removido",
        metadata={"document_name": document_name, "entity_type": entity_type},
        ip_address=ip_address,
        user_agent=user_agent,
    )


async def audit_team_member_assigned(
    db: AsyncSession,
    team_member_user_id: int,
    notice_id: int,
    user_id: int,
    notice_title: str,
    team_member_name: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
):
    """Audit when a team member is assigned to a notice."""
    await AuditService.create_audit_log(
        db=db,
        action=AuditAction.TEAM_MEMBER_ASSIGNED,
        entity_type=AuditEntityType.NOTICE,
        entity_id=notice_id,
        user_id=user_id,
        description=f"Membro '{team_member_name}' atribuído ao edital '{notice_title}'",
        metadata={
            "team_member_user_id": team_member_user_id,
            "notice_title": notice_title,
            "team_member_name": team_member_name,
        },
        ip_address=ip_address,
        user_agent=user_agent,
    )
