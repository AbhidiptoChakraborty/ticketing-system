from fastapi import FastAPI
from fastapi import Depends

from dotenv import load_dotenv
load_dotenv()

from app.auth.dependencies import get_current_user
from app.db.database import engine
from app.models.base import Base
from app.models import user
from app.routers import auth
from app.routers import users
from app.schemas.user import UserRead

app = FastAPI()


@app.on_event("startup")
async def startup():

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


app.include_router(auth.router)
app.include_router(users.router)


@app.get("/")
async def root():
    return {"message": "Ticketing System API"}


@app.get("/me", response_model=UserRead)
async def get_me(
    current_user=Depends(get_current_user)
):
    return current_user
