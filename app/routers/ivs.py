from typing import List

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_staff
from app.db.database import get_db
from app.schemas.ivs import IVSData
from app.schemas.user import User
from app.services import ivs_service
from app.services.excel_report_service import excel_report_service

router = APIRouter(prefix="/ivs", tags=["ivs"])


@router.get("/", response_model=List[IVSData])
async def read_ivs_data(
    user: User = Depends(require_staff), db: AsyncSession = Depends(get_db)
):
    """Retrieve IVS data for all students."""
    return await ivs_service.get_ivs_data(db)


@router.get("/export/excel")
async def export_ivs_excel(
    user: User = Depends(require_staff), db: AsyncSession = Depends(get_db)
):
    """
    Export IVS data to Excel file.

    This endpoint generates and returns an Excel file containing all IVS data
    with student information, notice details, scores, and expiration dates.
    """
    ivs_data = await ivs_service.get_ivs_data(db)

    excel_buffer = excel_report_service.generate_ivs_report(ivs_data)
    filename = excel_report_service.generate_filename()

    return StreamingResponse(
        io=excel_buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
