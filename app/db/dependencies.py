from app.db.database import _get_session_maker


async def get_db():
    SessionLocal = _get_session_maker()
    async with SessionLocal() as session:
        yield session
