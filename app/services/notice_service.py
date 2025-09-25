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
                selectinload(Notice.team_members),
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
                selectinload(Notice.team_members),
            )
            .offset(skip)
            .limit(limit)
        )

        if year:
            query = query.where(Notice.year == year)

        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def create_notice(
        db: AsyncSession, notice_data: NoticeCreate, creator_user_id: int
    ) -> Notice:
        db_notice = Notice(
            title=notice_data.title,
            notice_number=notice_data.notice_number,
            year=notice_data.year,
            start_date=notice_data.start_date,
            end_date=notice_data.end_date,
            responsible_agency=notice_data.responsible_agency,
            description=notice_data.description,
            auxilio_alimentacao=notice_data.auxilio_alimentacao,
            auxilio_moradia=notice_data.auxilio_moradia,
            auxilio_creche=notice_data.auxilio_creche,
            bolsa_pro_graduando=notice_data.bolsa_pro_graduando,
        )

        db.add(db_notice)
        await db.flush()

        for doc_data in notice_data.documents or []:
            db_document = Document(
                notice_id=db_notice.id,
                name=doc_data.name,
                file_url=doc_data.file_url,
                file_type=doc_data.file_type,
                file_size=doc_data.file_size,
            )
            db.add(db_document)

        for team_data in notice_data.team_members or []:
            db_team_member = NoticeTeam(
                notice_id=db_notice.id,
                user_id=team_data.user_id,
                role=team_data.role,
            )
            db.add(db_team_member)

        creator_in_team = any(
            member.user_id == creator_user_id
            for member in notice_data.team_members or []
        )
        if not creator_in_team:
            db_creator_team = NoticeTeam(
                notice_id=db_notice.id,
                user_id=creator_user_id,
                role="COORDINATOR",
            )
            db.add(db_creator_team)

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
                selectinload(Notice.team_members),
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
                selectinload(Notice.team_members),
            )
            .where(Notice.year == year)
        )
        return list(result.scalars().all())

    @staticmethod
    async def add_document_to_notice(
        db: AsyncSession, notice_id: int, document_data: dict
    ) -> Optional[Document]:
        notice = await NoticeService.get_notice_by_id(db, notice_id)
        if not notice:
            return None

        db_document = Document(
            notice_id=notice_id,
            name=document_data["name"],
            file_url=document_data["file_url"],
            file_type=document_data.get("file_type"),
            file_size=document_data.get("file_size"),
        )

        db.add(db_document)
        await db.commit()
        await db.refresh(db_document)

        return db_document

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
