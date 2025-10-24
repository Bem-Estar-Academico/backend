from datetime import timedelta
from typing import Dict, List, Sequence

from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.review import ReviewRegistrationModel
from app.models.registration import StudentRegistration
from app.models.notice import Notice
from app.models.notice import NoticeTeam
from app.schemas.ivs import IVSData
from sqlalchemy import select


async def get_ivs_data(db: AsyncSession) -> List[IVSData]:
    
    result = await db.execute(
        select(ReviewRegistrationModel)
        .options(
            joinedload(ReviewRegistrationModel.student_registration)
            .joinedload(StudentRegistration.student),
            
            joinedload(ReviewRegistrationModel.student_registration)
            .joinedload(StudentRegistration.notice)
            .selectinload(Notice.documents)
            
        )
        .options(
            joinedload(ReviewRegistrationModel.student_registration)
            .joinedload(StudentRegistration.notice)
            .selectinload(Notice.team_members)
            .joinedload(NoticeTeam.user)
        )
    )
    
    reviews: Sequence[ReviewRegistrationModel] = result.scalars().all()
    latest_reviews: Dict[int, ReviewRegistrationModel] = {}
    
    for review in reviews:
        student = review.student_registration.student
        if student.id not in latest_reviews:
            latest_reviews[student.id] = review
        else:
            new_end_date = review.student_registration.notice.registration_end_date
            existing_end_date = latest_reviews[student.id].student_registration.notice.registration_end_date
            if (
                new_end_date is not None and 
                existing_end_date is not None and 
                new_end_date > existing_end_date
            ):
                latest_reviews[student.id] = review

    ivs_data_list: List[IVSData] = []
    for review in latest_reviews.values():
        student = review.student_registration.student
        notice = review.student_registration.notice
        if notice.registration_end_date is not None:
            expiration_date = notice.registration_end_date + timedelta(days=365 * 2)
            ivs_data_list.append(
                IVSData(
                    student=student,
                    notice=notice,
                    ivs_score=review.ivs,
                    expiration_date=expiration_date,
                )
            )

    return ivs_data_list
