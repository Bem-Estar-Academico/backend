from typing import Any, Dict, Optional

from pydantic import BaseModel

from app.models.form_draft import FormSketchType


# Shared properties
class FormDraftBase(BaseModel):
    content: Optional[Dict[str, Any]] = None


# Properties to receive on item creation
class FormDraftCreate(FormDraftBase):
    notice_id: int
    user_id: int
    type: FormSketchType


# Properties to receive on item update
class FormDraftUpdate(FormDraftBase):
    pass


# Properties shared by models in DB
class FormDraftInDBBase(FormDraftBase):
    id: int
    notice_id: int
    user_id: int
    type: FormSketchType

    class Config:
        from_attributes = True


# Properties to return to client
class FormDraft(FormDraftInDBBase):
    pass


# Properties properties stored in DB
class FormDraftInDB(FormDraftInDBBase):
    pass
