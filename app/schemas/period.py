from datetime import datetime
from pydantic import BaseModel, ConfigDict

class PeriodBase(BaseModel):
    name: str
    init_date: datetime
    end_date: datetime
    
class PeriodCreate(PeriodBase):
    pass

class PeriodResponse(PeriodBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
