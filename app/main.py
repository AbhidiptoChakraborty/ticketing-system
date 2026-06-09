from dotenv import load_dotenv
from fastapi import Depends, FastAPI
from subprocess import run
import sys

from app.auth.dependencies import get_current_user
from app.models import user  # noqa: F401
from app.routers import auth
from app.routers import users
from app.routers import tickets
from app.routers import metrics as metrics_router
from app.schemas.user import UserRead
from app.metrics import metrics_middleware

load_dotenv()

app = FastAPI()

# attach metrics middleware early so all routes are measured
app.middleware("http")(metrics_middleware)


@app.on_event("startup")
async def startup():
    # Run Alembic migrations
    run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        check=True,
    )


app.include_router(auth.router)
app.include_router(users.router)
app.include_router(tickets.router)
app.include_router(metrics_router.router)


@app.get("/")
async def root():
    return {"message": "Ticketing System API"}


@app.get("/me", response_model=UserRead)
async def get_me(
    current_user=Depends(get_current_user)
):
    return current_user
