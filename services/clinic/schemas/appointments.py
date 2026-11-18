import uuid

from pydantic import BaseModel


class Booking(BaseModel):
    slot_id: uuid.UUID
    reminder_enabled: bool = False


class ReminderPreference(BaseModel):
    enabled: bool
