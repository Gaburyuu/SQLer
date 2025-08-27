import pytest

from sqler import AsyncSQLerDB, AsyncSQLerModel
from sqler.query import SQLerField as F


class AUser(AsyncSQLerModel):
    name: str
    age: int


@pytest.mark.asyncio
async def test_async_model_crud_and_query():
    db = AsyncSQLerDB.in_memory(shared=False)
    await db.connect()
    AUser.set_db(db)

    u = AUser(name="Alice", age=30)
    await u.save()
    assert u._id is not None

    u2 = await AUser.from_id(u._id)
    assert u2 and u2.name == "Alice"

    # query as models
    adults = await AUser.query().filter(F("age") >= 18).order_by("age").all()
    assert [a.name for a in adults] == ["Alice"]

    # update + refresh
    u.age = 31
    await u.save()
    u.age = 0
    await u.refresh()
    assert u.age == 31

    await db.close()

