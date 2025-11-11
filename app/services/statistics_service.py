from datetime import timedelta, date
from typing import List, Optional, Dict, Tuple
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from app.models.period import Period
from app.models.notice import Notice
from app.models.registration import StudentRegistration
from app.models.review import ReviewRegistrationModel

from app.schemas.statistics import (
    StatisticsResponse, AvgIVSReport, 
    StatusCountReport, StatusCount, ValidIVSCountReport
)

class StatisticsService:
    
    @staticmethod
    async def _find_relevant_notice_for_period(
        period: Period, all_notices: List[Notice]
    ) -> Optional[Notice]:
        """
        Encontra o edital correto para um período com base na sua regra:
        - Data de término do edital (registration_end_date) deve estar DENTRO do período.
        - Se houver múltiplos, usa o com a data de término MAIS RECENTE.
        """
        candidate_notices = []
        for notice in all_notices:
            if notice.registration_end_date and \
               period.init_date <= notice.registration_end_date <= period.end_date:
                candidate_notices.append(notice)
        
        if not candidate_notices:
            return None
        
        candidate_notices.sort(key=lambda x: x.registration_end_date, reverse=True)
        return candidate_notices[0]

    @staticmethod
    async def _get_all_valid_ivs_expirations(db: AsyncSession) -> List[Tuple[int, date]]:
        """
        Busca a última review APROVADA de CADA estudante e calcula sua data de
        expiração (updated_at + 2 anos).
        Retorna: Lista de (student_id, expiration_date)
        """
        APPROVED_STATUS = 'APPROVED' 
        
        latest_approved_review_sq = (
            select(
                StudentRegistration.student_id,
                func.max(ReviewRegistrationModel.updated_at).label('max_updated_at')
            )
            .join(ReviewRegistrationModel.student_registration)
            .where(ReviewRegistrationModel.status == APPROVED_STATUS)
            .group_by(StudentRegistration.student_id)
            .cte('latest_approved_review_sq')
        )

        query = (
            select(
                StudentRegistration.student_id,
                ReviewRegistrationModel.updated_at
            )
            .join(ReviewRegistrationModel.student_registration)
            .join(
                latest_approved_review_sq,
                and_(
                    StudentRegistration.student_id == latest_approved_review_sq.c.student_id,
                    ReviewRegistrationModel.updated_at == latest_approved_review_sq.c.max_updated_at
                )
            )
            .where(ReviewRegistrationModel.status == APPROVED_STATUS)
        )
        
        result = await db.execute(query)
        
        two_years = timedelta(days=730)
        expirations = [
            (row.student_id, row.updated_at.date() + two_years) 
            for row in result.all()
        ]
        
        return expirations

    @staticmethod
    async def get_dashboard_statistics(db: AsyncSession) -> StatisticsResponse:
        
        periods_query = select(Period).order_by(Period.init_date.desc())
        periods_result = await db.execute(periods_query)
        all_periods: List[Period] = list(periods_result.scalars().all())

        if not all_periods:
            return StatisticsResponse(
                avg_ivs_last_6_periods=[],
                status_counts_all_periods=[],
                valid_ivs_all_periods=[]
            )

        notices_query = select(Notice).where(Notice.registration_end_date.isnot(None))
        notices_result = await db.execute(notices_query)
        all_notices: List[Notice] = list(notices_result.scalars().all())

        valid_ivs_expirations = await StatisticsService._get_all_valid_ivs_expirations(db)
        
        avg_ivs_reports: List[AvgIVSReport] = []
        status_count_reports: List[StatusCountReport] = []
        valid_ivs_count_reports: List[ValidIVSCountReport] = []

        for period in all_periods:
            
            period_name = getattr(period, 'name', str(period.id))
            
            relevant_notice = await StatisticsService._find_relevant_notice_for_period(
                period, all_notices
            )
            
            current_avg_ivs: Optional[float] = None
            current_status_counts: List[StatusCount] = []
            
            if relevant_notice:
                ivs_query = (
                    select(func.avg(ReviewRegistrationModel.ivs))
                    .join(StudentRegistration)
                    .where(
                        StudentRegistration.notice_id == relevant_notice.id,
                        ReviewRegistrationModel.ivs.isnot(None)
                    )
                )
                avg_ivs_result = await db.execute(ivs_query)
                current_avg_ivs = avg_ivs_result.scalar_one_or_none()

                status_query = (
                    select(
                        ReviewRegistrationModel.status, 
                        func.count(ReviewRegistrationModel.id).label('count')
                    )
                    .join(StudentRegistration)
                    .where(StudentRegistration.notice_id == relevant_notice.id)
                    .group_by(ReviewRegistrationModel.status)
                )
                status_result = await db.execute(status_query)
                current_status_counts = [
                    StatusCount(status=row.status, count=row.count) 
                    for row in status_result.all()
                ]

            avg_ivs_reports.append(
                AvgIVSReport(
                    period_name=period_name, 
                    period_init_date=period.init_date,
                    average_ivs=current_avg_ivs
                )
            )
            
            status_count_reports.append(
                StatusCountReport(
                    period_name=period_name,
                    period_init_date=period.init_date,
                    counts=current_status_counts
                )
            )
            
            
            valid_count = 0
            period_start_date = period.init_date.date()
            
            for _student_id, expiration_date in valid_ivs_expirations:
                if expiration_date > period_start_date:
                    valid_count += 1
            
            valid_ivs_count_reports.append(
                ValidIVSCountReport(
                    period_name=period_name,
                    period_init_date=period.init_date,
                    count=valid_count
                )
            )

        avg_ivs_last_6 = avg_ivs_reports[:6]
        
        return StatisticsResponse(
            avg_ivs_last_6_periods=avg_ivs_last_6,
            status_counts_all_periods=status_count_reports,
            valid_ivs_all_periods=valid_ivs_count_reports
        )