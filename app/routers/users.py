from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from app.tasks.notifications import send_notification
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_role
from app.auth.security import hash_password
from app.db.dependencies import get_db
from app.models.user import User
from app.models.ticket import Ticket
from app.schemas.ticket import TicketRead
from app.schemas.user import UserCreate, UserRead, UserUpdate

router = APIRouter()


# CREATE USER
@router.post("/users", response_model=UserRead)
async def create_user(
    user: UserCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin"))
):
    result = await db.execute(
        select(User).where(User.username == user.username)
    )

    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Username already registered"
        )

    new_user = User(
        name=user.name,
        username=user.username,
        password_hash=hash_password(user.password),
        role=user.role
    )

    db.add(new_user)

    await db.commit()

    await db.refresh(new_user)

    background_tasks.add_task(
        send_notification,
        f"New user created: {new_user.name}"
    )

    return new_user


# GET ALL USERS
@router.get("/users", response_model=list[UserRead])
async def get_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin"))
):

    result = await db.execute(select(User))

    users = result.scalars().all()

    return users


# UPDATE USER
@router.put("/users/{user_id}", response_model=UserRead)
async def update_user(
    user_id: int,
    updated_user: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.id != user_id and current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Not enough permissions"
        )

    result = await db.execute(
        select(User).where(User.id == user_id)
    )

    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    user.name = updated_user.name

    await db.commit()

    await db.refresh(user)

    return user


# DELETE USER
@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin"))
):

    result = await db.execute(
        select(User).where(User.id == user_id)
    )

    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    await db.delete(user)

    await db.commit()

    return {"message": "User deleted"}


# GET TICKETS FOR A USER
@router.get("/users/{user_id}/tickets", response_model=list[TicketRead])
async def get_user_tickets(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.id != user_id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not enough permissions")

    result = await db.execute(
        select(Ticket).where(Ticket.owner_id == user_id)
    )

    tickets = result.scalars().all()

    return tickets
