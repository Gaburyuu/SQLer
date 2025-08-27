import pytest

from sqler import AsyncSQLerDB
from sqler.models.async_safe import AsyncSQLerSafeModel
from sqler.models import StaleVersionError
from sqler.query import SQLerField as F


class ACustomer(AsyncSQLerSafeModel):
    name: str
    tier: int


@pytest.mark.asyncio
async def test_async_safe_version_bumps_and_stale():
    db = AsyncSQLerDB.in_memory(shared=False)
    await db.connect()
    ACustomer.set_db(db)

    c = ACustomer(name="Bob", tier=1)
    await c.save()
    assert c._version == 0

    c.tier = 2
    await c.save()
    assert c._version == 1

    # stale
    await db.adapter.execute("UPDATE acustomers SET _version = _version + 1 WHERE _id = ?;", [c._id])
    await db.adapter.commit()

    c.tier = 3
    with pytest.raises(StaleVersionError):
        await c.save()

    await db.close()


@pytest.mark.asyncio
async def test_async_safe_query_and_refresh():
    db = AsyncSQLerDB.in_memory(shared=False)
    await db.connect()
    ACustomer.set_db(db)

    await ACustomer(name="A", tier=1).save()
    await ACustomer(name="B", tier=2).save()

    res = await ACustomer.query().filter(F("tier") >= 2).all()
    assert [r.name for r in res] == ["B"]

    first = await ACustomer.query().order_by("tier", desc=True).first()
    assert first is not None
    await first.refresh()
    assert first._version >= 0

    await db.close()

