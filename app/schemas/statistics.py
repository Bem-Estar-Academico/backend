from pydantic import BaseModel
from typing import List, Dict, Optional, Any
from datetime import date

class StatusCount(BaseModel):
    status: str
    count: int

class AvgIVSReport(BaseModel):
    period_name: str
    period_init_date: date
    average_ivs: Optional[float] = None

class StatusCountReport(BaseModel):
    period_name: str
    period_init_date: date
    counts: List[StatusCount]
    
class ValidIVSCountReport(BaseModel):
    period_name: str
    period_init_date: date
    count: int

class StatisticsResponse(BaseModel):
    avg_ivs_last_6_periods: List[AvgIVSReport]
    status_counts_all_periods: List[StatusCountReport]
    valid_ivs_all_periods: List[ValidIVSCountReport]