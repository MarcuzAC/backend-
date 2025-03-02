import asyncio
from sqlalchemy.ext.asyncio import AsyncEngine
from database import engine, Base  # Ensure you import the correct engine and Base

async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

asyncio.run(create_tables())
