from datetime import datetime
from pydantic import BaseModel
from typing import Optional


class TicketBase(BaseModel):
    title: str
    description: str


class TicketCreate(TicketBase):
    pass


class TicketUpdate(BaseModel):
    title: Optional[str]
    description: Optional[str]
    status: Optional[str]
    response: Optional[str]


class TicketRead(TicketBase):
    id: int
    owner_id: int
    status: str
    response: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
