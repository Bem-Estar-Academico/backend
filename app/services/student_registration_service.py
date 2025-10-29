from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.notice import Notice
from app.models.registration import RegistrationStatus, StudentRegistration
from app.models.user import User, UserType
from app.schemas.student_registration import (
    NoticeDetailsForRegistration,
    ReviewDetailsForRegistration,
    StudentRegistrationBase,
    StudentRegistrationUpdate,
    StudentRegistrationWithReviewResponse,
)


class StudentRegistrationService:
    """
    Service class responsible for managing student registrations for notices (editais).

    Handles creation, retrieval, updating, and deletion of registrations, including
    permission checks and validation against notice periods.
    """

    @staticmethod
    async def create_registration(
        notice_id: int,
        db: AsyncSession,
        registration_data: StudentRegistrationBase,
        student: User,
    ) -> StudentRegistration:
        """
        Registers a student for a specific notice.

        Performs checks for user type, notice existence, active registration period,
        and prevents duplicate registrations.

        Args:
            notice_id (int): The ID of the notice to register for.
            db (AsyncSession): The asynchronous database session.
            registration_data (StudentRegistrationCreate): Data containing registration answers/observations.
            student (User): The authenticated student user attempting to register.

        Returns:
            StudentRegistration: The newly created registration object.

        Raises:
            HTTPException: If the user is not a student (403), notice not found (404),
                           registration period is inactive (400), or already registered (400).
        """
        if student.user_type != UserType.STUDENT:
            raise HTTPException(
                status_code=403,
                detail="Apenas estudantes podem se inscrever em editais",
            )
        notice_query = select(Notice).where(Notice.id == notice_id)
        notice_result = await db.execute(notice_query)
        notice = notice_result.scalar_one_or_none()

        if not notice:
            raise HTTPException(status_code=404, detail="Edital não encontrado")

        now = datetime.now(timezone.utc)
        start_date = getattr(notice, "registration_start_date", None)
        end_date = getattr(notice, "registration_end_date", None)
        if (
            (start_date is not None and now < start_date)
            or (end_date is not None and now > end_date)
        ):
            raise HTTPException(
                status_code=400, detail="Período de inscrições não está ativo"
            )

        existing_query = select(StudentRegistration).where(
            and_(
                StudentRegistration.student_id == student.id,
                StudentRegistration.notice_id == notice_id,
            )
        )
        existing_result = await db.execute(existing_query)
        existing_registration = existing_result.scalar_one_or_none()
        if existing_registration:
            raise HTTPException(
                status_code=400, detail="Estudante já inscrito neste edital"
            )

        registration = StudentRegistration(
            student_id=student.id,
            notice_id=notice_id,
            answer=registration_data.answer,
            status=RegistrationStatus.PENDING,
        )
        db.add(registration)
        await db.commit()
        await db.refresh(registration)

        return registration

    @staticmethod
    async def get_registration_by_id(
        db: AsyncSession, registration_id: int
    ) -> Optional[StudentRegistration]:
        """
        Retrieves a single student registration by its ID, eagerly loading student and notice details.

        Args:
            db (AsyncSession): The asynchronous database session.
            registration_id (int): The ID of the registration record.

        Returns:
            Optional[StudentRegistration]: The registration object, or None if not found.
        """
        query = (
            select(StudentRegistration)
            .options(
                selectinload(StudentRegistration.student),
                selectinload(StudentRegistration.notice),
            )
            .where(StudentRegistration.id == registration_id)
        )
        result = await db.execute(query)
        data = result.scalar_one_or_none()

        return data

    @staticmethod
    async def get_registrations_by_notice(
        db: AsyncSession,
        notice_id: int,
        status: Optional[RegistrationStatus] = None,
    ) -> tuple[List[StudentRegistration], int]:
        """
        Retrieves a list of registrations for a specific notice, with optional filtering by status.

        Includes a total count of matching registrations.

        Args:
            db (AsyncSession): The asynchronous database session.
            notice_id (int): The ID of the notice.
            status (Optional[RegistrationStatus]): Optional filter by registration status.

        Returns:
            tuple[List[StudentRegistration], int]: A tuple containing the list of registrations
                                                   and the total count of matching records.
        """
        query = (
            select(StudentRegistration)
            .options(
                selectinload(StudentRegistration.student),
                selectinload(StudentRegistration.notice),
            )
            .where(StudentRegistration.notice_id == notice_id)
        )

        if status:
            query = query.where(StudentRegistration.status == status)

        count_query = (
            select(func.count())
            .select_from(StudentRegistration)
            .where(StudentRegistration.notice_id == notice_id)
        )

        if status:
            count_query = count_query.where(StudentRegistration.status == status)

        count_result = await db.execute(count_query)
        total = count_result.scalar_one()

        query = query.order_by(StudentRegistration.registration_date.desc())
        result = await db.execute(query)
        registrations = list(result.scalars().all())

        return registrations, total

    @staticmethod
    async def get_registrations_by_student(
        db: AsyncSession,
        student_id: int,
    ) -> tuple[List[StudentRegistration], int]:
        """
        Retrieves all registrations submitted by a specific student.

        Includes a total count of the student's registrations.

        Args:
            db (AsyncSession): The asynchronous database session.
            student_id (int): The ID of the student user.

        Returns:
            tuple[List[StudentRegistration], int]: A tuple containing the list of registrations
                                                   and the total count of the student's registrations.
        """
        query = (
            select(StudentRegistration)
            .options(
                selectinload(StudentRegistration.student),
                selectinload(StudentRegistration.notice),
            )
            .where(StudentRegistration.student_id == student_id)
            .order_by(StudentRegistration.registration_date.desc())
        )

        count_query = (
            select(func.count())
            .select_from(StudentRegistration)
            .where(StudentRegistration.student_id == student_id)
        )

        count_result = await db.execute(count_query)
        total = count_result.scalar_one()

        result = await db.execute(query)
        registrations = list(result.scalars().all())

        return registrations, total

    @staticmethod
    async def update_registration(
        db: AsyncSession,
        registration_id: int,
        registration_data: StudentRegistrationUpdate,
        current_user: User,
    ) -> StudentRegistration:
        """
        Updates a registration status or answer, applying permission rules.

        Students can only update (cancel) their own registrations. Staff/Coordinators can update status/answer.

        Args:
            db (AsyncSession): The asynchronous database session.
            registration_id (int): The ID of the registration to update.
            registration_data (StudentRegistrationUpdate): The data containing the updates.
            current_user (User): The authenticated user performing the update.

        Returns:
            StudentRegistration: The updated registration object.

        Raises:
            HTTPException: If registration is not found (404) or user lacks permission (403).
        """
        registration = await StudentRegistrationService.get_registration_by_id(
            db, registration_id
        )
        if not registration:
            raise HTTPException(status_code=404, detail="Inscrição não encontrada")

        if current_user.user_type == UserType.STUDENT:
            if registration.student_id != current_user.id:
                raise HTTPException(
                    status_code=403,
                    detail="Você só pode modificar suas próprias inscrições",
                )
            if (
                registration_data.status
                and registration_data.status != RegistrationStatus.CANCELLED
            ):
                raise HTTPException(
                    status_code=403,
                    detail="Estudantes só podem cancelar suas inscrições",
                )

        elif not current_user.is_staff:
            raise HTTPException(
                status_code=403, detail="Sem permissão para modificar inscrições"
            )

        if registration_data.status is not None:
            registration.status = registration_data.status
        if registration_data.answer is not None:
            registration.answer = registration_data.answer

        await db.commit()
        await db.refresh(registration)

        return registration

    @staticmethod
    async def delete_registration(
        db: AsyncSession,
        registration_id: int,
        current_user: User,
    ) -> bool:
        """
        Deletes a registration record, applying permission rules.

        Students can only delete their own registrations. Staff/Coordinators can delete any registration.

        Args:
            db (AsyncSession): The asynchronous database session.
            registration_id (int): The ID of the registration to delete.
            current_user (User): The authenticated user performing the deletion.

        Returns:
            bool: True if the deletion was successful.

        Raises:
            HTTPException: If registration is not found (404) or user lacks permission (403).
        """
        registration = await StudentRegistrationService.get_registration_by_id(
            db, registration_id
        )
        if not registration:
            raise HTTPException(status_code=404, detail="Inscrição não encontrada")

        if current_user.user_type == UserType.STUDENT:
            if registration.student_id != current_user.id:
                raise HTTPException(
                    status_code=403,
                    detail="Você só pode deletar suas próprias inscrições",
                )
        # Assuming that 'is_staff' is an attribute available on User for Coordinator/SocialWorker roles
        elif not current_user.is_staff:
            raise HTTPException(
                status_code=403, detail="Sem permissão para deletar inscrições"
            )

        await db.delete(registration)
        await db.commit()

        return True

    @staticmethod
    async def get_student_registration_for_notice(
        db: AsyncSession,
        student_id: int,
        notice_id: int,
    ) -> Optional[StudentRegistration]:
        """
        Retrieves a single registration record based on a specific student and notice combination.

        Args:
            db (AsyncSession): The asynchronous database session.
            student_id (int): The ID of the student.
            notice_id (int): The ID of the notice.

        Returns:
            Optional[StudentRegistration]: The registration object, or None if the student is not registered for the notice.
        """
        query = (
            select(StudentRegistration)
            .options(
                selectinload(StudentRegistration.student),
                selectinload(StudentRegistration.notice),
            )
            .where(
                and_(
                    StudentRegistration.student_id == student_id,
                    StudentRegistration.notice_id == notice_id,
                )
            )
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_student_registrations_with_reviews(
        db: AsyncSession, student_id: int
    ) -> List[StudentRegistrationWithReviewResponse]:
        """
        Retrieves all registrations for a student, including notice and review details.

        Args:
            db (AsyncSession): The asynchronous database session.
            student_id (int): The ID of the student.

        Returns:
            List[StudentRegistrationWithReviewResponse]: A list of registrations with details.
        """
        query = (
            select(StudentRegistration)
            .options(
                selectinload(StudentRegistration.notice),
                selectinload(StudentRegistration.review),
            )
            .where(StudentRegistration.student_id == student_id)
            .order_by(StudentRegistration.registration_date.desc())
        )

        result = await db.execute(query)
        registrations = result.scalars().all()

        response_list: List[StudentRegistrationWithReviewResponse] = []
        for reg in registrations:
            notice_details = NoticeDetailsForRegistration.model_validate(reg.notice)

            review_details = None
            if reg.review:
                expires_at = None
                if reg.notice.registration_end_date:
                    expires_at = reg.notice.registration_end_date + timedelta(days=730)

                review_details = ReviewDetailsForRegistration(
                    id=reg.review.id,
                    status=reg.status,
                    ivs=reg.review.ivs,
                    expires_at=expires_at,
                )

            response_list.append(
                StudentRegistrationWithReviewResponse(
                    notice=notice_details,
                    review=review_details,
                )
            )

        return response_list