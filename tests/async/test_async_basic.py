import pytest
import asyncio

import pytest_asyncio

from sqler.adapter import AsyncSQLiteAdapter
from sqler.db.async_db import AsyncSQLerDB
from sqler.query.async_query import AsyncSQLerQuery
from sqler.query import SQLerField as F


@pytest.mark.asyncio
async def test_async_adapter_connect_execute():
    adapter = AsyncSQLiteAdapter.in_memory(shared=False)
    await adapter.connect()
    await adapter.execute("CREATE TABLE t (_id INTEGER PRIMARY KEY, data JSON NOT NULL)")
    await adapter.execute("INSERT INTO t (data) VALUES (json(?))", ["{\"a\":1}"])
    await adapter.commit()
    cur = await adapter.execute("SELECT json_extract(data,'$.a') FROM t")
    row = await cur.fetchone()
    assert row[0] == 1
    await adapter.close()


@pytest.mark.asyncio
async def test_async_db_insert_find_and_query():
    db = AsyncSQLerDB.in_memory(shared=False)
    await db.connect()
    _id = await db.insert_document("users", {"name": "Ada", "age": 36})
    doc = await db.find_document("users", _id)
    assert doc["name"] == "Ada"

    q = AsyncSQLerQuery("users", adapter=db.adapter).filter(F("age") >= 30)
    rows = await q.all_dicts()
    assert rows and rows[0]["name"] == "Ada"
    await db.close()

