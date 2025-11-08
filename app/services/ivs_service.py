from datetime import timedelta
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import contains_eager

from app.models.notice import Notice, NoticeTeam
from app.models.registration import StudentRegistration
from app.models.review import ReviewRegistrationModel
from app.schemas.ivs import IVSData


async def get_ivs_data(db: AsyncSession) -> List[IVSData]:
    """
    Fetches the most recent IVS data for each student (PostgreSQL optimized).
    """
    stmt = (
        select(ReviewRegistrationModel)
        .distinct(StudentRegistration.student_id)
        .join(ReviewRegistrationModel.student_registration)
        .join(StudentRegistration.notice)
        .where(Notice.registration_end_date.isnot(None))
        .order_by(
            StudentRegistration.student_id, ReviewRegistrationModel.created_at.desc()
        )
        .options(
            contains_eager(ReviewRegistrationModel.student_registration)
            .contains_eager(StudentRegistration.notice)
            .selectinload(Notice.documents),
            contains_eager(ReviewRegistrationModel.student_registration)
            .contains_eager(StudentRegistration.notice)
            .selectinload(Notice.team_members)
            .joinedload(NoticeTeam.user),
            contains_eager(ReviewRegistrationModel.student_registration).joinedload(
                StudentRegistration.student
            ),
        )
    )

    result = await db.execute(stmt)
    reviews = result.scalars().unique().all()

    return [
        IVSData(
            student=review.student_registration.student,
            notice=review.student_registration.notice,
            ivs_score=review.ivs,
            expiration_date=review.student_registration.notice.registration_end_date
            + timedelta(days=730),
        )
        for review in reviews
        if review.student_registration.notice.registration_end_date is not None
    ]
