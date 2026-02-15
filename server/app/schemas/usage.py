from datetime import datetime

from pydantic import BaseModel


class UsageTodayResponse(BaseModel):
    used: int
    reserved: int
    limit: int
    remaining: int
    resets_at: datetime
