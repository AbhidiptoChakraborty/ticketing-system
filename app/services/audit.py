from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity import TicketActivity


def record_ticket_activity(
    db: AsyncSession,
    *,
    ticket_id: int,
    actor_id: int,
    event_type: str,
    details: dict[str, Any] | None = None,
) -> TicketActivity:
    """Stage an audit event in the current transaction."""
    activity = TicketActivity(
        ticket_id=ticket_id,
        actor_id=actor_id,
        event_type=event_type,
        details=details or {},
    )
    db.add(activity)
    return activity
