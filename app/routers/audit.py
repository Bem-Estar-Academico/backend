"""
Router for audit log endpoints.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_coordinator
from app.db.database import get_db
from app.models.audit import AuditAction, AuditEntityType, AuditLog
from app.models.user import User
from app.schemas.audit import AuditLogResponse
from app.services.audit_service import AuditService

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/", response_model=List[AuditLogResponse])
async def get_audit_logs(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(
        100, ge=1, le=500, description="Maximum number of records to return"
    ),
    action: Optional[AuditAction] = Query(None, description="Filter by action type"),
    entity_type: Optional[AuditEntityType] = Query(
        None, description="Filter by entity type"
    ),
    entity_id: Optional[int] = Query(None, description="Filter by entity ID"),
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    current_user: User = Depends(require_coordinator),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieve audit logs with optional filters.

    This endpoint is restricted to coordinators only for security and compliance purposes.

    Args:
        skip: Number of records to skip for pagination
        limit: Maximum number of records to return
        action: Optional filter by action type
        entity_type: Optional filter by entity type
        entity_id: Optional filter by specific entity ID
        user_id: Optional filter by user who performed the action
        current_user: Authenticated coordinator user
        db: Database session

    Returns:
        List of audit log entries matching the filters
    """
    audit_logs = await AuditService.get_audit_logs(
        db=db,
        skip=skip,
        limit=limit,
        action_filter=action,
        entity_type_filter=entity_type,
        entity_id_filter=entity_id,
        user_id_filter=user_id,
    )

    return audit_logs


@router.get("/entity/{entity_type}/{entity_id}", response_model=List[AuditLogResponse])
async def get_audit_logs_for_entity(
    entity_type: AuditEntityType,
    entity_id: int = Path(..., ge=1, description="Entity ID must be positive"),
    limit: int = Query(
        50, ge=1, le=200, description="Maximum number of records to return"
    ),
    current_user: User = Depends(require_coordinator),
    db: AsyncSession = Depends(get_db),
):
    """
    Get audit logs for a specific entity.

    This endpoint returns the audit trail for a specific entity (notice, review, etc.).

    Args:
        entity_type: The type of entity to get audit logs for
        entity_id: The ID of the entity to get audit logs for
        limit: Maximum number of records to return
        current_user: Authenticated coordinator user
        db: Database session

    Returns:
        List of audit log entries for the specified entity
    """
    audit_logs = await AuditService.get_audit_logs_for_entity(
        db=db, entity_type=entity_type, entity_id=entity_id, limit=limit
    )

    return audit_logs


@router.get("/stats", response_model=Dict[str, Any])
async def get_audit_stats(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    current_user: User = Depends(require_coordinator),
    db: AsyncSession = Depends(get_db),
):
    """
    Get audit log statistics for the specified period.

    Args:
        days: Number of days to analyze (default: 30)
        current_user: Authenticated coordinator user
        db: Database session

    Returns:
        Dictionary containing audit statistics
    """
    start_date = datetime.now(timezone.utc) - timedelta(days=days)

    action_stats = await db.execute(
        select(AuditLog.action, func.count(AuditLog.id))
        .where(AuditLog.created_at >= start_date)
        .group_by(AuditLog.action)
    )

    entity_stats = await db.execute(
        select(AuditLog.entity_type, func.count(AuditLog.id))
        .where(AuditLog.created_at >= start_date)
        .group_by(AuditLog.entity_type)
    )

    total_count = await db.execute(
        select(func.count(AuditLog.id)).where(AuditLog.created_at >= start_date)
    )

    return {
        "period_days": days,
        "start_date": start_date.isoformat(),
        "total_actions": total_count.scalar(),
        "actions_by_type": {
            action.value: count for action, count in action_stats.fetchall()
        },
        "actions_by_entity_type": {
            entity_type.value: count for entity_type, count in entity_stats.fetchall()
        },
    }
