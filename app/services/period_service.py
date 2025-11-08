from sqlalchemy.orm import Session
from app.models.period import Period
from app.schemas.period import PeriodCreate

class PeriodService:
    
    async def create_period(db: Session, period: PeriodCreate) -> Period:
        period_data = period.model_dump()
        
        db_period = Period(**period_data)
        
        db.add(db_period)
        await db.commit()
        await db.refresh(db_period)
        
        return db_period