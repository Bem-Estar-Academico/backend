from typing import List

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.period import Period
from app.schemas.period import PeriodCreate, PeriodResponse, PeriodUpdate
from app.services.period_service import PeriodService

router = APIRouter(tags=["periods"], prefix="/periods")


@router.post(
    "/",
    response_model=PeriodResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cria um novo período",
)
async def create_period(
    period: PeriodCreate, db: AsyncSession = Depends(get_db)
) -> PeriodResponse:

    period_res = await PeriodService.create_period(db=db, period=period)

    return period_res


@router.get("/", response_model=List[PeriodResponse], summary="Lista todos os períodos")
async def get_all_periods(db: AsyncSession = Depends(get_db)) -> List[Period]:
    """
    Get all periods
    """
    periods = await PeriodService.get_all_periods(db=db)

    return periods


@router.put(
    "/{periodo_id}",
    response_model=PeriodResponse,
    summary="Atualiza um período existente",
)
async def update_period(
    period_id: int, period: PeriodUpdate, db: AsyncSession = Depends(get_db)
) -> Period:
    """
    Update a period by its ID.
    """

    period = await PeriodService.update_period(
        db=db, period_id=period_id, period=period
    )

    return period


@router.delete(
    "/{periodo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deleta um período existente",
)
async def delete_period(period_id: int, db: AsyncSession = Depends(get_db)) -> Response:
    """
    Delete a period by its ID.

    It's OK, return the status 204 No Content.
    """

    await PeriodService.delete_period(db=db, period_id=period_id)

    return Response(status_code=status.HTTP_204_NO_CONTENT)
