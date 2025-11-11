from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.schemas.statistics import StatisticsResponse
from app.services.statistics_service import StatisticsService
# from app.dependencies.auth import get_current_active_user 

router = APIRouter(
    prefix="/statistics",
    tags=["Statistics"],
    # dependencies=[Depends(get_current_active_user)] 
)

@router.get(
    "/dashboard",
    response_model=StatisticsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Aggregated Dashboard Statistics",
    description="""
    Retorna dados agregados complexos para o dashboard, agrupados por períodos.

    - **avg_ivs_last_6_periods**: Média de IVS dos editais vinculados aos últimos 6 períodos.
    - **status_counts_all_periods**: Contagem de status de inscrição dos editais vinculados a todos os períodos.
    - **valid_ivs_all_periods**: Contagem de estudantes com IVS válido (aprovado e não expirado) no início de cada período.
    """
)
async def get_dashboard_data(
    db: AsyncSession = Depends(get_db)
) -> StatisticsResponse:
    """
    Constrói e retorna o relatório de estatísticas do dashboard.
    """
    return await StatisticsService.get_dashboard_statistics(db)