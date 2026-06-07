from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

import os

DATABASE_URL = os.getenv("DATABASE_URL")

# Lazy engine creation - only create when DATABASE_URL is set
engine = None
AsyncSessionLocal = None


def _get_engine():
    global engine
    if engine is None:
        if not DATABASE_URL:
            raise RuntimeError(
                "DATABASE_URL environment variable not set"
            )
        engine = create_async_engine(DATABASE_URL, echo=True)
    return engine


def _get_session_maker():
    global AsyncSessionLocal
    if AsyncSessionLocal is None:
        AsyncSessionLocal = sessionmaker(
            bind=_get_engine(),
            class_=AsyncSession,
            expire_on_commit=False
        )
    return AsyncSessionLocal
