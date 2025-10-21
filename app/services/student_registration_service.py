from datetime import datetime, timezone
from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.notice import Notice, RegistrationStatus, StudentRegistration
from app.models.user import User, UserType
from app.schemas.student_registration import (
    StudentRegistrationCreate,
    StudentRegistrationUpdate,
)


class StudentRegistrationService:
    @staticmethod
    async def create_registration(
        db: AsyncSession,
        registration_data: StudentRegistrationCreate,
        student: User,
    ) -> StudentRegistration:
        if student.user_type != UserType.STUDENT:
            raise HTTPException(
                status_code=403,
                detail="Apenas estudantes podem se inscrever em editais",
            )

        notice_query = select(Notice).where(Notice.id == registration_data.notice_id)
        notice_result = await db.execute(notice_query)
        notice = notice_result.scalar_one_or_none()

        if not notice:
            raise HTTPException(status_code=404, detail="Edital não encontrado")

        now = datetime.now(timezone.utc)
        if now < notice.registration_start_date or now > notice.registration_end_date:
            raise HTTPException(
                status_code=400, detail="Período de inscrições não está ativo"
            )

        existing_query = select(StudentRegistration).where(
            and_(
                StudentRegistration.student_id == student.id,
                StudentRegistration.notice_id == registration_data.notice_id,
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
            notice_id=registration_data.notice_id,
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
        query = (
            select(StudentRegistration)
            .options(
                selectinload(StudentRegistration.student),
                selectinload(StudentRegistration.notice),
            )
            .where(StudentRegistration.id == registration_id)
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_registrations_by_notice(
        db: AsyncSession,
        notice_id: int,
        status: Optional[RegistrationStatus] = None,
    ) -> tuple[list[StudentRegistration], int]:
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
        registrations = result.scalars().all()

        return registrations, total

    @staticmethod
    async def get_registrations_by_student(
        db: AsyncSession,
        student_id: int,
    ) -> tuple[list[StudentRegistration], int]:
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
        registrations = result.scalars().all()

        return registrations, total

    @staticmethod
    async def update_registration(
        db: AsyncSession,
        registration_id: int,
        registration_data: StudentRegistrationUpdate,
        current_user: User,
    ) -> StudentRegistration:
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