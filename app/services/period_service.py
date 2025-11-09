from typing import List
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.period import Period
from app.schemas.period import PeriodCreate, PeriodUpdate

from app.core.logging_config import get_logger
logger = get_logger(__name__)

class PeriodService:
    
    @staticmethod
    async def create_period(db: AsyncSession, period: PeriodCreate) -> Period:
        period_data = period.model_dump()
        
        db_period = Period(**period_data)
        
        if db_period.init_date > db_period.end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Período não pode ter uma data de inicio após a data de fim",
            )
            
        db.add(db_period)
        await db.commit()
        await db.refresh(db_period)
        
        
        return db_period
    
    @staticmethod
    async def get_all_periods(db: AsyncSession) -> List[Period]:
        """
        get all period in the database.
        """
        
        query = select(Period).order_by(Period.init_date)

        result = await db.execute(query)

        return list(result.scalars().all())
    
    @staticmethod
    async def get_period_by_id(
        db: AsyncSession, period_id: int
    ) -> Period:
        """
        Busca um período pelo seu ID.
        """
        query = select(Period).where(Period.id == period_id)
        result = await db.execute(query)
        period = result.scalar_one_or_none()

        if not period:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Período não encontrado",
            )
            
        
        return period

    @staticmethod
    async def update_period(
        db: AsyncSession, period_id: int, period: PeriodUpdate
    ) -> Period:
        "Update the period"
        
        db_period = await PeriodService.get_period_by_id(db=db, period_id=period_id)
        
        if (period.init_date and period.end_date) and period.init_date > period.end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Período não pode ter uma data de inicio após a data de fim",
            )
            
        update_data = period.model_dump(exclude_unset=True)
        
        for key, value in update_data.items():
            setattr(db_period, key, value)

        db.add(db_period)
        await db.commit()
        await db.refresh(db_period)

        return db_period
    
    @staticmethod
    async def delete_period(db: AsyncSession, period_id: int) -> None:
        """
        Delete a period by your ID.
        """
        
        db_period = await PeriodService.get_period_by_id(
            db=db, period_id=period_id
        )
        
        await db.delete(db_period)
        
        await db.commit()