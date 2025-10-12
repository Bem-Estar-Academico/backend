from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.notice import Notice, RegistrationStatus, StudentRegistration
from app.models.user import User, UserType
from app.schemas.student_registration import (
    StudentRegistrationCreate,
    StudentRegistrationUpdate,
)


class StudentRegistrationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_registration(
        self,
        registration_data: StudentRegistrationCreate,
        student: User,
    ) -> StudentRegistration:
        if student.user_type != UserType.STUDENT:
            raise HTTPException(
                status_code=403,
                detail="Apenas estudantes podem se inscrever em editais",
            )

        notice_query = select(Notice).where(Notice.id == registration_data.notice_id)
        notice_result = await self.db.execute(notice_query)
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
        existing_result = await self.db.execute(existing_query)
        existing_registration = existing_result.scalar_one_or_none()

        if existing_registration:
            raise HTTPException(
                status_code=400, detail="Estudante já inscrito neste edital"
            )

        registration = StudentRegistration(
            student_id=student.id,
            notice_id=registration_data.notice_id,
            notes=registration_data.notes,
            status=RegistrationStatus.PENDING,
        )

        self.db.add(registration)
        await self.db.commit()
        await self.db.refresh(registration)

        return registration

    async def get_registration_by_id(
        self, registration_id: int
    ) -> Optional[StudentRegistration]:

        query = (
            select(StudentRegistration)
            .options(
                selectinload(StudentRegistration.student),
                selectinload(StudentRegistration.notice),
            )
            .where(StudentRegistration.id == registration_id)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_registrations_by_notice(
        self,
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

        count_query = select(StudentRegistration).where(
            StudentRegistration.notice_id == notice_id
        )
        if status:
            count_query = count_query.where(StudentRegistration.status == status)

        count_result = await self.db.execute(count_query)
        total = len(count_result.scalars().all())

        query = query.order_by(StudentRegistration.registration_date.desc())
        result = await self.db.execute(query)
        registrations = result.scalars().all()

        return list(registrations), total

    async def get_registrations_by_student(
        self,
        student_id: int,
    ) -> tuple[list[StudentRegistration], int]:
        query = (
            select(StudentRegistration)
            .options(
                selectinload(StudentRegistration.student),
                selectinload(StudentRegistration.notice),
            )
            .where(StudentRegistration.student_id == student_id)
        )

        count_query = select(StudentRegistration).where(
            StudentRegistration.student_id == student_id
        )

        count_result = await self.db.execute(count_query)
        total = len(count_result.scalars().all())

        query = query.order_by(StudentRegistration.registration_date.desc())
        result = await self.db.execute(query)
        registrations = result.scalars().all()

        return list(registrations), total

    async def update_registration(
        self,
        registration_id: int,
        registration_data: StudentRegistrationUpdate,
        current_user: User,
    ) -> StudentRegistration:
        registration = await self.get_registration_by_id(registration_id)
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
        if registration_data.notes is not None:
            registration.notes = registration_data.notes

        await self.db.commit()
        await self.db.refresh(registration)

        return registration

    async def delete_registration(
        self,
        registration_id: int,
        current_user: User,
    ) -> bool:

        registration = await self.get_registration_by_id(registration_id)
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

        await self.db.delete(registration)
        await self.db.commit()

        return True

    async def get_student_registration_for_notice(
        self,
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
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
