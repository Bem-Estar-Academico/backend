from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.notice import Document, Notice, NoticeTeam
from app.schemas.notice import NoticeCreate, NoticeUpdate


class NoticeService:

    @staticmethod
    async def get_notice_by_id(db: AsyncSession, notice_id: int) -> Optional[Notice]:
        result = await db.execute(
            select(Notice)
            .options(
                selectinload(Notice.documents),
                selectinload(Notice.team_members).selectinload(NoticeTeam.user),
            )
            .where(Notice.id == notice_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_notices(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        year: Optional[int] = None,
    ) -> List[Notice]:
        query = (
            select(Notice)
            .options(
                selectinload(Notice.documents),
                selectinload(Notice.team_members).selectinload(NoticeTeam.user),
            )
            .offset(skip)
            .limit(limit)
        )

        if year:
            query = query.where(Notice.year == year)

        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def create_notice(db: AsyncSession, notice_data: NoticeCreate) -> Notice:
        db_notice = Notice(
            title=notice_data.title,
            notice_number=notice_data.notice_number,
            year=notice_data.year,
            start_date=notice_data.start_date,
            end_date=notice_data.end_date,
            responsible_agency=notice_data.responsible_agency,
            description=notice_data.description,
            food_allowance=notice_data.food_allowance,
            housing_allowance=notice_data.housing_allowance,
            daycare_allowance=notice_data.daycare_allowance,
            graduation_scholarship=notice_data.graduation_scholarship,
        )

        db.add(db_notice)
        await db.flush()

        await db.commit()
        await db.refresh(db_notice)

        return await NoticeService.get_notice_by_id(db, db_notice.id)

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
            .options(
                selectinload(Notice.documents),
                selectinload(Notice.team_members).selectinload(NoticeTeam.user),
            )
            .where(Notice.start_date <= current_time)
            .where(Notice.end_date >= current_time)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_notices_by_year(db: AsyncSession, year: int) -> List[Notice]:
        result = await db.execute(
            select(Notice)
            .options(
                selectinload(Notice.documents),
                selectinload(Notice.team_members).selectinload(NoticeTeam.user),
            )
            .where(Notice.year == year)
        )
        return list(result.scalars().all())

    @staticmethod
    async def add_team_member_to_notice(
        db: AsyncSession, notice_id: int, user_id: int, role: str
    ) -> Optional[NoticeTeam]:
        notice = await NoticeService.get_notice_by_id(db, notice_id)
        if not notice:
            return None

        existing_member = await db.execute(
            select(NoticeTeam)
            .where(NoticeTeam.notice_id == notice_id)
            .where(NoticeTeam.user_id == user_id)
        )
        if existing_member.scalar_one_or_none():
            return None

        db_team_member = NoticeTeam(
            notice_id=notice_id,
            user_id=user_id,
            role=role,
        )

        db.add(db_team_member)
        await db.commit()
        await db.refresh(db_team_member)

        return db_team_member

    @staticmethod
    async def upload_document_to_notice(
        db: AsyncSession,
        notice_id: int,
        file_content: bytes,
        filename: str,
        content_type: str,
    ) -> Optional[Document]:
        from app.core.s3_manager import s3_manager

        notice = await NoticeService.get_notice_by_id(db, notice_id)
        if not notice:
            return None

        try:
            file_key = s3_manager.upload_file(file_content, filename, content_type)

            db_document = Document(
                notice_id=notice_id,
                name=filename,
                file_key=file_key,
                file_type=content_type,
                file_size=len(file_content),
            )

            db.add(db_document)
            await db.commit()
            await db.refresh(db_document)

            return db_document

        except Exception as e:
            await db.rollback()
            raise Exception(f"Error uploading document: {str(e)}")

    @staticmethod
    async def delete_document(db: AsyncSession, document_id: int) -> bool:
        from app.core.s3_manager import s3_manager

        result = await db.execute(select(Document).where(Document.id == document_id))
        document = result.scalar_one_or_none()

        if not document:
            return False

        s3_manager.delete_file(document.file_key)

        await db.delete(document)
        await db.commit()

        return True

    @staticmethod
    async def get_document_download_url(
        db: AsyncSession, document_id: int, expiration: int = 3600
    ) -> Optional[str]:
        from app.core.s3_manager import s3_manager

        result = await db.execute(select(Document).where(Document.id == document_id))
        document = result.scalar_one_or_none()

        if not document:
            return None

        return s3_manager.generate_presigned_download_url(document.file_key, expiration)
