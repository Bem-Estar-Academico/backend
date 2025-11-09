from typing import List
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.period import Period
from app.schemas.period import PeriodCreate

class PeriodService:
    
    async def create_period(db: AsyncSession, period: PeriodCreate) -> Period:
        period_data = period.model_dump()
        
        db_period = Period(**period_data)
        
        db.add(db_period)
        await db.commit()
        await db.refresh(db_period)
        
        return db_period
    
    async def get_all_periods(db: AsyncSession) -> List[Period]:
        """
        get all period in the database.
        """
        
        query = select(Period).order_by(Period.init_date)

        result = await db.execute(query)

        return list(result.scalars().all())