from fastapi import APIRouter, Depends, status 
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.schemas.period import PeriodCreate, PeriodResponse
from app.services.period_service import PeriodService 

router = APIRouter()

@router.post(
    "/",
    response_model=PeriodResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cria um novo período"
)
async def create_period(
    period: PeriodCreate,
    db: AsyncSession = Depends(get_db)
) -> PeriodResponse:
    
    period_res = await PeriodService.create_period(db=db, period=period)
    
    return period_res