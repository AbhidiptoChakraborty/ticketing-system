from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from app.tasks.notifications import send_notification
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.dependencies import get_db
from app.models.user import User
from app.schemas.user import UserCreate

router = APIRouter()

# CREATE USER
@router.post("/users")
async def create_user(
    user: UserCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):

    new_user = User(name=user.name)

    db.add(new_user)

    await db.commit()

    await db.refresh(new_user)

    background_tasks.add_task(
        send_notification,
        f"New user created: {new_user.name}"
    )

    return {
        "id": new_user.id,
        "name": new_user.name
    }


# GET ALL USERS
@router.get("/users")
async def get_users(
    db: AsyncSession = Depends(get_db)
):

    result = await db.execute(select(User))

    users = result.scalars().all()

    return users


# UPDATE USER
@router.put("/users/{user_id}")
async def update_user(
    user_id: int,
    updated_user: UserCreate,
    db: AsyncSession = Depends(get_db)
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

    user.name = updated_user.name

    await db.commit()

    await db.refresh(user)

    return user


# DELETE USER
@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db)
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