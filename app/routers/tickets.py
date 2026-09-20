from typing import Literal, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_role
from app.db.dependencies import get_db
from app.models.comment import TicketComment
from app.models.ticket import Ticket
from app.models.user import User
from app.schemas.ticket import DashboardRead, TicketCommentCreate, TicketCommentRead, TicketCreate, TicketPage, TicketRead, TicketUpdate
from app.tasks.notifications import send_notification

router = APIRouter(prefix="/tickets", tags=["tickets"])


def _ticket_scope(current_user: User):
    return [] if current_user.role == "admin" else [Ticket.owner_id == current_user.id]


async def _find_accessible_ticket(ticket_id: int, db: AsyncSession, current_user: User) -> Ticket:
    ticket = await db.scalar(select(Ticket).where(Ticket.id == ticket_id))
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if current_user.role != "admin" and ticket.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return ticket


@router.post("", response_model=TicketRead, status_code=status.HTTP_201_CREATED)
async def create_ticket(ticket: TicketCreate, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    new_ticket = Ticket(title=ticket.title, description=ticket.description, priority=ticket.priority, category=ticket.category.upper(), status="OPEN", owner_id=current_user.id)
    db.add(new_ticket)
    await db.commit()
    await db.refresh(new_ticket)
    background_tasks.add_task(send_notification, f"New {new_ticket.priority} ticket: {new_ticket.title} (id={new_ticket.id})")
    return new_ticket


@router.get("", response_model=TicketPage)
async def list_tickets(
    status_filter: Optional[str] = Query(default=None, alias="status"), priority: Optional[str] = None,
    category: Optional[str] = None, q: Optional[str] = Query(default=None, min_length=1, max_length=100),
    page: int = Query(default=1, ge=1), page_size: int = Query(default=20, ge=1, le=100),
    sort: Literal["newest", "oldest", "priority"] = "newest", db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Filter the queue by triage fields, search text, and paginate results."""
    filters = _ticket_scope(current_user)
    if status_filter:
        filters.append(Ticket.status == status_filter.upper())
    if priority:
        filters.append(Ticket.priority == priority.upper())
    if category:
        filters.append(Ticket.category == category.upper())
    if q:
        pattern = f"%{q}%"
        filters.append(or_(Ticket.title.ilike(pattern), Ticket.description.ilike(pattern)))
    total = await db.scalar(select(func.count()).select_from(Ticket).where(*filters))
    priority_rank = case(
        {"URGENT": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}, value=Ticket.priority, else_=0
    )
    order_by = {"newest": Ticket.created_at.desc(), "oldest": Ticket.created_at.asc(), "priority": priority_rank.desc()}[sort]
    result = await db.execute(select(Ticket).where(*filters).order_by(order_by, Ticket.id.desc()).offset((page - 1) * page_size).limit(page_size))
    return TicketPage(items=result.scalars().all(), total=total or 0, page=page, page_size=page_size)


@router.get("/dashboard", response_model=DashboardRead)
async def ticket_dashboard(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """A compact, permission-aware dashboard for the current ticket queue."""
    filters = _ticket_scope(current_user)
    status_rows = await db.execute(select(Ticket.status, func.count(Ticket.id)).where(*filters).group_by(Ticket.status))
    priority_rows = await db.execute(select(Ticket.priority, func.count(Ticket.id)).where(*filters).group_by(Ticket.priority))
    by_status, by_priority = dict(status_rows.all()), dict(priority_rows.all())
    return DashboardRead(total=sum(by_status.values()), open=by_status.get("OPEN", 0), in_progress=by_status.get("IN_PROGRESS", 0), waiting_on_customer=by_status.get("WAITING_ON_CUSTOMER", 0), resolved=by_status.get("RESOLVED", 0), closed=by_status.get("CLOSED", 0), urgent=by_priority.get("URGENT", 0), high=by_priority.get("HIGH", 0))


@router.get("/{ticket_id}", response_model=TicketRead)
async def get_ticket(ticket_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    return await _find_accessible_ticket(ticket_id, db, current_user)


@router.patch("/{ticket_id}", response_model=TicketRead)
@router.put("/{ticket_id}", response_model=TicketRead, include_in_schema=False)
async def update_ticket(ticket_id: int, updated: TicketUpdate, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_role("admin"))):
    ticket = await _find_accessible_ticket(ticket_id, db, current_user)
    for field, value in updated.model_dump(exclude_unset=True).items():
        setattr(ticket, field, value.upper() if field == "category" and value else value)
    await db.commit()
    await db.refresh(ticket)
    return ticket


@router.get("/{ticket_id}/comments", response_model=list[TicketCommentRead])
async def list_comments(ticket_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    await _find_accessible_ticket(ticket_id, db, current_user)
    result = await db.execute(select(TicketComment).where(TicketComment.ticket_id == ticket_id).order_by(TicketComment.created_at))
    return result.scalars().all()


@router.post("/{ticket_id}/comments", response_model=TicketCommentRead, status_code=status.HTTP_201_CREATED)
async def add_comment(ticket_id: int, payload: TicketCommentCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    await _find_accessible_ticket(ticket_id, db, current_user)
    comment = TicketComment(ticket_id=ticket_id, author_id=current_user.id, body=payload.body)
    db.add(comment)
    await db.commit()
    await db.refresh(comment)
    return comment


@router.delete("/{ticket_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ticket(ticket_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_role("admin"))):
    ticket = await _find_accessible_ticket(ticket_id, db, current_user)
    await db.delete(ticket)
    await db.commit()
