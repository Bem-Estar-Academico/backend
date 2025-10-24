from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.schemas.ivs import IVSData
from app.services import ivs_service

router = APIRouter(prefix="/ivs", tags=["ivs"])

@router.get("/", response_model=List[IVSData])
async def read_ivs_data(db: AsyncSession = Depends(get_db)):
    """Retrieve IVS data for all students."""
    return await ivs_service.get_ivs_data(db)
