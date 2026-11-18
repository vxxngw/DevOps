import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class DoctorInput(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    specialty: str = Field(min_length=1, max_length=100)
    active: bool = True


class SlotInput(BaseModel):
    doctor_id: uuid.UUID
    starts_at: datetime
    ends_at: datetime
