from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.notice import Notice
from app.schemas.notice import NoticeCreate, NoticeUpdate


class NoticeService:

    @staticmethod
    async def get_notice_by_id(db: AsyncSession, notice_id: int) -> Optional[Notice]:
        result = await db.execute(
            select(Notice)
            .options(selectinload(Notice.coordinator))
            .where(Notice.id == notice_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_notices(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        coordinator_id: Optional[int] = None,
    ) -> List[Notice]:
        query = (
            select(Notice)
            .options(selectinload(Notice.coordinator))
            .offset(skip)
            .limit(limit)
        )

        if coordinator_id:
            query = query.where(Notice.coordinator_id == coordinator_id)

        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def create_notice(db: AsyncSession, notice_data: NoticeCreate) -> Notice:
        db_notice = Notice(
            title=notice_data.title,
            description=notice_data.description,
            important_dates=notice_data.important_dates,
            start_date=notice_data.start_date,
            end_date=notice_data.end_date,
            document_url=notice_data.document_url,
            coordinator_id=notice_data.coordinator_id,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        db.add(db_notice)
        await db.commit()
        await db.refresh(db_notice)

        return db_notice

    @staticmethod
    async def update_notice(
        db: AsyncSession, notice_id: int, notice_update: NoticeUpdate
    ) -> Optional[Notice]:
        notice = await NoticeService.get_notice_by_id(db, notice_id)
        if not notice:
            return None

        update_data = notice_update.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(notice, field, value)

        notice.updated_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(notice)

        return notice

    @staticmethod
    async def delete_notice(db: AsyncSession, notice_id: int) -> bool:
        notice = await NoticeService.get_notice_by_id(db, notice_id)
        if not notice:
            return False

        await db.delete(notice)
        await db.commit()
        return True

    @staticmethod
    async def get_active_notices(db: AsyncSession) -> List[Notice]:
        current_time = datetime.now(timezone.utc)
        result = await db.execute(
            select(Notice)
            .options(selectinload(Notice.coordinator))
            .where(Notice.start_date <= current_time)
            .where(Notice.end_date >= current_time)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_notices_by_coordinator(
        db: AsyncSession, coordinator_id: int
    ) -> List[Notice]:
        result = await db.execute(
            select(Notice)
            .options(selectinload(Notice.coordinator))
            .where(Notice.coordinator_id == coordinator_id)
        )
        return list(result.scalars().all())
