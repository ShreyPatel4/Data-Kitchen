from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from nova_api.config import settings


def _create_engine():
    kwargs = {"echo": settings.debug}
    # SQLite doesn't support pool_size/max_overflow
    if "sqlite" not in settings.database_url:
        kwargs["pool_size"] = 20
        kwargs["max_overflow"] = 10
    return create_async_engine(settings.database_url, **kwargs)


engine = _create_engine()
async_session = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
