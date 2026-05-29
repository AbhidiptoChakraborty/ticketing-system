from fastapi import FastAPI

from app.db.database import engine
from app.models.base import Base
from app.models import user
from app.routers import users

app = FastAPI()


@app.on_event("startup")
async def startup():

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


app.include_router(users.router)


@app.get("/")
async def root():
    return {"message": "Ticketing System API"}