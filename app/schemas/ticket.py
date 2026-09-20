from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

TicketStatus = Literal[
    "OPEN",
    "IN_PROGRESS",
    "WAITING_ON_CUSTOMER",
    "RESOLVED",
    "CLOSED",
]
TicketPriority = Literal["LOW", "MEDIUM", "HIGH", "URGENT"]


class TicketBase(BaseModel):
    title: str = Field(
        min_length=3,
        max_length=160,
        examples=["Unable to access billing portal"],
    )
    description: str = Field(min_length=5, max_length=5000)


class TicketCreate(TicketBase):
    priority: TicketPriority = "MEDIUM"
    category: str = Field(default="GENERAL", min_length=2, max_length=50)


class TicketUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=3, max_length=160)
    description: Optional[str] = Field(
        default=None,
        min_length=5,
        max_length=5000,
    )
    status: Optional[TicketStatus] = None
    response: Optional[str] = Field(default=None, max_length=5000)
    priority: Optional[TicketPriority] = None
    category: Optional[str] = Field(default=None, min_length=2, max_length=50)


class TicketRead(TicketBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    status: str
    response: Optional[str]
    priority: str
    category: str
    created_at: datetime
    updated_at: datetime


class TicketCommentCreate(BaseModel):
    body: str = Field(min_length=1, max_length=5000)


class TicketCommentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_id: int
    author_id: int
    body: str
    created_at: datetime


class TicketActivityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_id: int
    actor_id: int
    event_type: str
    details: dict
    created_at: datetime


class TicketPage(BaseModel):
    items: list[TicketRead]
    total: int
    page: int
    page_size: int


class DashboardRead(BaseModel):
    total: int
    open: int
    in_progress: int
    waiting_on_customer: int
    resolved: int
    closed: int
    urgent: int
    high: int
