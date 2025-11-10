from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional


from sqlalchemy import case, delete, extract, select
from sqlalchemy import TEXT, case, cast, extract, func, select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.storage_factory import get_storage_manager
from app.models.notice import Document, Notice, NoticeTeam, StudentRegistration
from app.models.review import RegistrationStatus, ReviewRegistrationModel
from app.models.user import User, UserType
from app.schemas.notice import NoticeCreate, NoticeUpdate
from app.schemas.notice import NoticeCreate, NoticeTeamMember, NoticeUpdate, NoticeStatisticsResponse


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
            query = query.where(extract("year", Notice.created_at) == year)

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
        await db.flush()  # Flush to get db_notice.id

        # Assign the creator of the notice as a team member
        db_team_member = NoticeTeam(
            notice_id=db_notice.id,
            user_id=created_by_user_id,
        )
        db.add(db_team_member)

        # Assign additional team members, ensuring no invalid IDs are processed
        if notice_data.team_members:
            # Remove the creator's ID from the list to avoid adding them twice
            team_members_to_add = [id for id in notice_data.team_members if id != created_by_user_id]
            # Validate all team member IDs before processing
            invalid_ids = [id for id in team_members_to_add if id <= 0]
            if invalid_ids:
                raise ValueError(f"Invalid user IDs: {invalid_ids}")
            for team_member_id in team_members_to_add:
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

        update_data = notice_update.model_dump(exclude_unset=True, exclude={"team_members"})

        for field, value in update_data.items():
            setattr(notice, field, value)
            
        if notice_update.team_members is not None:
            await NoticeService._handle_team_update(
                db=db, notice=notice, new_team_ids=notice_update.team_members
            )

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
    async def get_notices_for_student(
        db: AsyncSession,
        student_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Retrieves notices with registration status for a specific student.
        Uses a single optimized query with LEFT JOIN to get registration status.

        Args:
            db (AsyncSession): The asynchronous database session.
            student_id (int): The ID of the student.
            skip (int): The number of items to skip (for pagination).
            limit (int): The maximum number of items to return (for pagination).

        Returns:
            List[Dict[str, Any]]: A list of notice data with registration status.
        """
        if student_id <= 0:
            raise ValueError(f"Invalid student ID: {student_id}")

        query = (
            select(
                Notice,
                case((StudentRegistration.id.is_not(None), True), else_=False).label(
                    "is_registered"
                ),
            )
            .outerjoin(
                StudentRegistration,
                (StudentRegistration.notice_id == Notice.id)
                & (StudentRegistration.student_id == student_id),
            )
            .options(selectinload(Notice.documents))
            .offset(skip)
            .limit(limit)
        )

        result = await db.execute(query)

        notices_data: List[Dict[str, Any]] = []
        for row in result:
            notice = row.Notice
            is_registered = row.is_registered

            notice_dict: Dict[str, Any] = {
                "id": notice.id,
                "title": notice.title,
                "registration_start_date": notice.registration_start_date,
                "registration_end_date": notice.registration_end_date,
                "appeal_start_date": notice.appeal_start_date,
                "appeal_end_date": notice.appeal_end_date,
                "preliminary_result_date": notice.preliminary_result_date,
                "final_result_date": notice.final_result_date,
                "description": notice.description,
                "food_allowance": notice.food_allowance,
                "housing_allowance": notice.housing_allowance,
                "daycare_allowance": notice.daycare_allowance,
                "graduation_scholarship": notice.graduation_scholarship,
                "created_at": notice.created_at,
                "updated_at": notice.updated_at,
                "documents": [
                    {
                        "id": doc.id,
                        "notice_id": doc.notice_id,
                        "name": doc.name,
                        "file_key": doc.file_key,
                        "file_type": doc.file_type,
                        "file_size": doc.file_size,
                        "uploaded_at": doc.uploaded_at,
                        "file_url": doc.file_url,
                    }
                    for doc in notice.documents
                ],
                "is_registered": is_registered,
            }
            notices_data.append(notice_dict)

        return notices_data

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
            .where(extract("year", Notice.created_at) == year)
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
        if user_id <= 0:
            raise ValueError(f"Invalid user ID: {user_id}")

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

        storage_manager = get_storage_manager()

        notice = await NoticeService.get_notice_by_id(db, notice_id)
        if not notice:
            return None

        try:
            file_key = storage_manager.upload_file(file_content, filename, content_type)

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

        storage_manager = get_storage_manager()

        result = await db.execute(select(Document).where(Document.id == document_id))
        document = result.scalar_one_or_none()

        if not document:
            return False

        storage_manager.delete_file(document.file_key)

        await db.delete(document)
        await db.commit()

        return True

    @staticmethod
    async def get_document_download_url(
        db: AsyncSession, document_id: int, expiration: int = 3600
    ) -> Optional[str]:
        # First, get the document
        """
        Generates a temporary, presigned URL for direct download of a document from S3.

        Args:
            db (AsyncSession): The asynchronous database session.
            document_id (int): The ID of the document.
            expiration (int): The expiration time in seconds for the generated URL (default: 3600 seconds/1 hour).

        Returns:
            Optional[str]: The presigned download URL, or None if the document was not found.
        """
        storage_manager = get_storage_manager()

        result = await db.execute(select(Document).where(Document.id == document_id))
        document = result.scalar_one_or_none()

        if not document:
            return None

        return storage_manager.generate_signed_url(document.file_key, expiration)

    @staticmethod
    async def get_team_for_notice(
        db: AsyncSession, notice_id: int
    ) -> List[Dict[str, Any]]:
        """
        Retrieves the list of team members for a specific notice.

        Args:
            db (AsyncSession): The asynchronous database session.
            notice_id (int): The ID of the notice.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries, each formatted to match
                                  the full User schema + 'last_review'.
        """
        from sqlalchemy import func

        sq = (
            select(ReviewRegistrationModel.updated_at)
            .where(ReviewRegistrationModel.social_worker_id == User.id)
            .order_by(ReviewRegistrationModel.updated_at.desc())
            .limit(1)
            .as_scalar()
        )

        q = (
            select(
                User.id,
                User.email,
                User.full_name,
                User.is_active,
                User.user_type,
                sq.label("last_review"),
            )
            .join(NoticeTeam, NoticeTeam.user_id == User.id)
            .where(NoticeTeam.notice_id == notice_id)
            .order_by(User.full_name)
        )

        total_registrations_result = await db.execute(
            select(func.count(StudentRegistration.id)).where(
                StudentRegistration.notice_id == notice_id
            )
        )
        total_registrations = total_registrations_result.scalar_one()

        progress = 0
        if total_registrations > 0:
            final_status_registrations_result = await db.execute(
                select(func.count(StudentRegistration.id))
                .join(ReviewRegistrationModel)
                .where(StudentRegistration.notice_id == notice_id)
                .where(
                    ReviewRegistrationModel.status.in_(
                        [
                            RegistrationStatus.APPROVED,
                            RegistrationStatus.REJECTED,
                            RegistrationStatus.CANCELLED,
                        ]
                    )
                )
            )
            final_status_registrations = (
                final_status_registrations_result.scalar_one()
            )
            progress = (final_status_registrations / total_registrations) * 100

        result = await db.execute(q)

        team_members_formatted: List[Dict[str, Any]] = []
        for row in result.mappings():
            member_data: Dict[str, Any] = dict(row)

            if member_data["user_type"] == UserType.SOCIAL_WORKER:
                progress_query = (
                    select(
                        func.count().label("total_reviews"),
                        func.sum(
                            case(
                                (
                                    ReviewRegistrationModel.status.in_(
                                        [
                                            RegistrationStatus.APPROVED,
                                            RegistrationStatus.REJECTED,
                                        ]
                                    ),
                                    1,
                                ),
                                else_=0,
                            )
                        ).label("completed_reviews"),
                    )
                    .select_from(ReviewRegistrationModel)
                    .join(
                        StudentRegistration,
                        ReviewRegistrationModel.student_registration_id
                        == StudentRegistration.id,
                    )
                    .where(
                        ReviewRegistrationModel.social_worker_id == member_data["id"]
                    )
                    .where(StudentRegistration.notice_id == notice_id)
                )

                progress_result = await db.execute(progress_query)
                progress_data = progress_result.first()

                if progress_data and progress_data.total_reviews > 0:
                    completed = progress_data.completed_reviews or 0
                    total = progress_data.total_reviews
                    member_data["progress"] = round((completed / total) * 100, 1)
                else:
                    member_data["progress"] = 0.0
            else:
                # Para coordenadores, não calculamos progresso baseado em revisões
                member_data["progress"] = 100.0

            team_members_formatted.append(member_data)

        return team_members_formatted
    
    @staticmethod
    async def _handle_team_update(
        db: AsyncSession, notice: Notice, new_team_ids: List[int]
    ) -> None:
        """
        Lógica separada para atualizar a equipe de um edital.
        Compara a equipe atual com a nova lista e faz as adições/remoções.
        """
        
        query = select(NoticeTeam.user_id).where(NoticeTeam.notice_id == notice.id)
        result = await db.execute(query)
        current_team_ids = set(result.scalars().all())
        
        new_team_ids_set = set(new_team_ids)

        ids_to_add = new_team_ids_set - current_team_ids
        ids_to_remove = current_team_ids - new_team_ids_set
        
        if ids_to_remove:
            logging.info(f"Removendo {len(ids_to_remove)} membros do edital {notice.id}")
            delete_stmt = (
                delete(NoticeTeam)
                .where(NoticeTeam.notice_id == notice.id)
                .where(NoticeTeam.user_id.in_(ids_to_remove))
            )
            await db.execute(delete_stmt)

        if ids_to_add:
            logging.info(f"Adicionando {len(ids_to_add)} novos membros ao edital {notice.id}")
            
            user_check_query = select(User.id).where(
                User.id.in_(ids_to_add),
                User.user_type.in_([UserType.SOCIAL_WORKER, UserType.COORDINATOR])
            )
            valid_users = set((await db.execute(user_check_query)).scalars().all())
            
            for user_id in ids_to_add:
                if user_id in valid_users:
                    new_member = NoticeTeam(notice_id=notice.id, user_id=user_id)
                    db.add(new_member)
                else:
                    logging.warning(f"Usuário ID {user_id} não é válido ou não é assistente/coordenador. Pulando.")

    @staticmethod
    async def get_notice_statistics(
        db: AsyncSession, notice_id: int
    ) -> NoticeStatisticsResponse:
        """
        Calcula e retorna estatísticas de contagem de inscrições e equipe
        para um edital.
        """

        status_case = case(
            (ReviewRegistrationModel.id.is_(None), RegistrationStatus.PENDING.value),
            else_=cast(ReviewRegistrationModel.status, TEXT),
        ).label("status")

        registrations_query = (
            select(
                status_case,
                func.count(StudentRegistration.id).label("count"),
            )
            .select_from(StudentRegistration)
            .outerjoin(
                ReviewRegistrationModel,
                StudentRegistration.id == ReviewRegistrationModel.student_registration_id
            )
            .where(StudentRegistration.notice_id == notice_id)
            .group_by(status_case)
        )

        social_worker_query = (
            select(func.count(User.id))
            .join(NoticeTeam, User.id == NoticeTeam.user_id)
            .where(NoticeTeam.notice_id == notice_id)
            .where(User.user_type == UserType.SOCIAL_WORKER)
        )

        registrations_result = await db.execute(registrations_query)
        social_worker_result = await db.execute(social_worker_query)

        rows = registrations_result.mappings().all()
        counts = {s.value: 0 for s in RegistrationStatus}
        total_count = 0
        for row in rows:
            status_key = row["status"] 
            count = row["count"]
            
            if status_key:
                counts[status_key] = count
                total_count += count

        social_worker_count = social_worker_result.scalar_one_or_none() or 0

        return NoticeStatisticsResponse(
            pending_count=counts.get(RegistrationStatus.PENDING.value, 0),
            review_count=counts.get(RegistrationStatus.REVIEW.value, 0),
            approved_count=counts.get(RegistrationStatus.APPROVED.value, 0),
            rejected_count=counts.get(RegistrationStatus.REJECTED.value, 0),
            appeal_count=counts.get(RegistrationStatus.APPEAL.value, 0),
            cancelled_count=counts.get(RegistrationStatus.CANCELLED.value, 0),
            total_count=total_count,
            social_worker_count=social_worker_count,
        )

