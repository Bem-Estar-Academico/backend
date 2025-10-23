from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.notice import Document, Notice, NoticeTeam
from app.models.user import User, UserType
from app.schemas.notice import NoticeCreate, NoticeUpdate


class NoticeService:
    """
    Service class responsible for all CRUD and related business logic for notices (editais).

    It manages database interactions, eager loading of related entities (documents, team members),
    and external integrations like S3 file management.
    """

    @staticmethod
    async def get_notice_by_id(db: AsyncSession, notice_id: int) -> Optional[Notice]:
        """
        Retrieves a single notice by its unique ID, eagerly loading related documents and team members.

        Args:
            db (AsyncSession): The asynchronous database session.
            notice_id (int): The ID of the notice to retrieve.

        Returns:
            Optional[Notice]: The fully loaded Notice object, or None if not found.
        """
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
        """
        Retrieves a list of notices with optional filtering by year and pagination.

        Eagerly loads related documents and team members for efficiency.

        Args:
            db (AsyncSession): The asynchronous database session.
            skip (int): The number of records to skip (for pagination).
            limit (int): The maximum number of records to return.
            year (Optional[int]): Optional filter to retrieve notices from a specific year.

        Returns:
            List[Notice]: A list of Notice objects.
        """
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
    async def create_notice(
        db: AsyncSession, notice_data: NoticeCreate, created_by_user_id: int
    ) -> Notice:
        """
        Creates a new notice and automatically assigns the creator as the first COORDINATOR team member.

        Args:
            db (AsyncSession): The asynchronous database session.
            notice_data (NoticeCreate): Pydantic schema with the notice data.
            created_by_user_id (int): The ID of the user creating the notice.

        Returns:
            Notice: The newly created and refreshed Notice object with relations loaded.
        """
        db_notice = Notice(
            title=notice_data.title,
            registration_start_date=notice_data.registration_start_date,
            registration_end_date=notice_data.registration_end_date,
            appeal_start_date=notice_data.appeal_start_date,
            appeal_end_date=notice_data.appeal_end_date,
            preliminary_result_date=notice_data.preliminary_result_date,
            final_result_date=notice_data.final_result_date,
            description=notice_data.description,
            food_allowance=notice_data.food_allowance,
            housing_allowance=notice_data.housing_allowance,
            daycare_allowance=notice_data.daycare_allowance,
            graduation_scholarship=notice_data.graduation_scholarship,
        )

        db.add(db_notice)
        await db.flush() # Flush to get db_notice.id
        db_team_member = NoticeTeam(
            notice_id=db_notice.id,
            user_id=created_by_user_id,
        )
        db.add(db_team_member)
        if notice_data.team_members:
            for team_member_id in notice_data.team_members:
                if team_member_id != created_by_user_id:
                    db_additional_member = NoticeTeam(
                        notice_id=db_notice.id,
                        user_id=team_member_id,
                    )
                    db.add(db_additional_member)

        await db.commit()
        await db.refresh(db_notice)

        return await NoticeService.get_notice_by_id(db, db_notice.id)

    @staticmethod
    async def update_notice(
        db: AsyncSession, notice_id: int, notice_update: NoticeUpdate
    ) -> Optional[Notice]:
        """
        Updates an existing notice with the provided data. Only fields present in `notice_update` are modified.

        Args:
            db (AsyncSession): The asynchronous database session.
            notice_id (int): The ID of the notice to update.
            notice_update (NoticeUpdate): Pydantic schema with the fields to update.

        Returns:
            Optional[Notice]: The updated Notice object, or None if the notice was not found.
        """
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
        """
        Deletes a notice by its ID.

        Args:
            db (AsyncSession): The asynchronous database session.
            notice_id (int): The ID of the notice to delete.

        Returns:
            bool: True if the notice was deleted, False if it was not found.
        """
        notice = await NoticeService.get_notice_by_id(db, notice_id)
        if not notice:
            return False

        await db.delete(notice)
        await db.commit()
        return True

    @staticmethod
    async def get_active_notices(db: AsyncSession) -> List[Notice]:
        """
        Retrieves all notices that are currently open for registration.

        A notice is considered active if the current UTC time is between
        `registration_start_date` and `registration_end_date`.

        Args:
            db (AsyncSession): The asynchronous database session.

        Returns:
            List[Notice]: A list of active Notice objects.
        """
        current_time = datetime.now(timezone.utc)
        result = await db.execute(
            select(Notice)
            .options(
                selectinload(Notice.documents),
                selectinload(Notice.team_members).selectinload(NoticeTeam.user),
            )
            .where(Notice.registration_start_date <= current_time)
            .where(Notice.registration_end_date >= current_time)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_notices_by_year(db: AsyncSession, year: int) -> List[Notice]:
        """
        Retrieves all notices published in a specific year.

        Args:
            db (AsyncSession): The asynchronous database session.
            year (int): The year to filter by.

        Returns:
            List[Notice]: A list of Notice objects from the specified year.
        """
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
        db: AsyncSession, notice_id: int, user_id: int
    ) -> Optional[NoticeTeam]:
        """
        Adds a user as a team member to a specific notice. Prevents duplicate assignments.

        Args:
            db (AsyncSession): The asynchronous database session.
            notice_id (int): The ID of the notice.
            user_id (int): The ID of the user to be added.
            role (str): The role of the user (e.g., 'COORDINATOR').

        Returns:
            Optional[NoticeTeam]: The newly created NoticeTeam assignment, or None if the notice
                                  doesn't exist or the member is already assigned.
        """
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
        )

        db.add(db_team_member)
        await db.commit()

        # Retrieve the created member with user details loaded
        result = await db.execute(
            select(NoticeTeam)
            .options(selectinload(NoticeTeam.user))
            .where(NoticeTeam.id == db_team_member.id)
        )
        db_team_member = result.scalar_one()

        return db_team_member

    @staticmethod
    async def upload_document_to_notice(
        db: AsyncSession,
        notice_id: int,
        file_content: bytes,
        filename: str,
        content_type: str,
    ) -> Optional[Document]:
        """
        Uploads a file to S3 storage and records the document metadata in the database.

        Args:
            db (AsyncSession): The asynchronous database session.
            notice_id (int): The ID of the notice to attach the document to.
            file_content (bytes): The binary content of the file.
            filename (str): The original filename.
            content_type (str): The MIME type of the file.

        Returns:
            Optional[Document]: The newly created Document object, or None if the notice was not found.

        Raises:
            Exception: If an error occurs during the S3 upload or database transaction.
        """
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
        """
        Deletes a document record from the database and removes the corresponding file from S3.

        Args:
            db (AsyncSession): The asynchronous database session.
            document_id (int): The ID of the document to delete.

        Returns:
            bool: True if the document was deleted, False if it was not found.
        """
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
        """
        Generates a temporary, presigned URL for direct download of a document from S3.

        Args:
            db (AsyncSession): The asynchronous database session.
            document_id (int): The ID of the document.
            expiration (int): The expiration time in seconds for the generated URL (default: 3600 seconds/1 hour).

        Returns:
            Optional[str]: The presigned download URL, or None if the document was not found.
        """
        from app.core.s3_manager import s3_manager

        result = await db.execute(select(Document).where(Document.id == document_id))
        document = result.scalar_one_or_none()

        if not document:
            return None

        return s3_manager.generate_presigned_download_url(document.file_key, expiration)