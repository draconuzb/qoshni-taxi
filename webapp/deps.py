from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database import async_session

PAGE_SIZE = 20

templates = Jinja2Templates(directory="webapp/templates")


async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session
