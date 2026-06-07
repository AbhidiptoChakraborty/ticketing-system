from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_role
from app.db.dependencies import get_db
from app.models.ticket import Ticket
from app.schemas.ticket import TicketCreate, TicketRead, TicketUpdate
from app.tasks.notifications import send_notification

router = APIRouter()


@router.post(
    "/tickets",
    response_model=TicketRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_ticket(
    ticket: TicketCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    new_ticket = Ticket(
        title=ticket.title,
        description=ticket.description,
        status="OPEN",
        owner_id=current_user.id
    )

    db.add(new_ticket)
    await db.commit()
    await db.refresh(new_ticket)

    background_tasks.add_task(
        send_notification,
        f"New ticket created: {new_ticket.title} (id={new_ticket.id})"
    )

    return new_ticket


@router.get("/tickets", response_model=list[TicketRead])
async def list_tickets(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if current_user.role == "admin":
        result = await db.execute(select(Ticket))
    else:
        result = await db.execute(
            select(Ticket).where(Ticket.owner_id == current_user.id)
        )

    tickets = result.scalars().all()
    return tickets


@router.get("/tickets/{ticket_id}", response_model=TicketRead)
async def get_ticket(
    ticket_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    ticket = result.scalar_one_or_none()

    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    # Authorization: admins can see all, users only their own
    if current_user.role != "admin" and ticket.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return ticket


@router.put("/tickets/{ticket_id}", response_model=TicketRead)
async def update_ticket(
    ticket_id: int,
    updated: TicketUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    ticket = result.scalar_one_or_none()

    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    if updated.title is not None:
        ticket.title = updated.title
    if updated.description is not None:
        ticket.description = updated.description
    if updated.status is not None:
        ticket.status = updated.status
    if updated.response is not None:
        ticket.response = updated.response

    await db.commit()
    await db.refresh(ticket)

    return ticket


@router.delete("/tickets/{ticket_id}")
async def delete_ticket(
    ticket_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    ticket = result.scalar_one_or_none()

    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    await db.delete(ticket)
    await db.commit()

    return {"message": "Ticket deleted"}
