import pytest

from sqler.adapter import AsyncSQLiteAdapter
from sqler.db.async_db import AsyncSQLerDB


@pytest.fixture
async def async_adapter():
    adapter = AsyncSQLiteAdapter.in_memory(shared=False)
    await adapter.connect()
    try:
        yield adapter
    finally:
        await adapter.close()


@pytest.fixture
async def async_db():
    db = AsyncSQLerDB.in_memory(shared=False)
    await db.connect()
    try:
        yield db
    finally:
        await db.close()

