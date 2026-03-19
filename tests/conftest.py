import asyncio
import os
import sys
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# Ensure the API source is on the path
sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "apps", "api", "src")
)

# Override database URL before importing app
os.environ["NOVA_DATABASE_URL"] = "sqlite+aiosqlite:///./test.db"
os.environ["NOVA_DEBUG"] = "false"

from nova_api.app import create_app  # noqa: E402
from nova_api.database import Base, get_db  # noqa: E402


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


test_engine = create_async_engine(
    "sqlite+aiosqlite:///./test.db", echo=False
)
test_session_factory = async_sessionmaker(
    test_engine, expire_on_commit=False
)


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with test_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@pytest_asyncio.fixture
async def client():
    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as ac:
        yield ac
