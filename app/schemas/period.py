from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

class PeriodBase(BaseModel):
    name: str
    init_date: datetime
    end_date: datetime
    
class PeriodCreate(PeriodBase):
    pass

class PeriodUpdate(BaseModel):
    name: Optional[str] = None
    init_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

class PeriodResponse(PeriodBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
