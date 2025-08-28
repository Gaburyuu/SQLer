from __future__ import annotations

from typing import Optional
from sqler import SQLerDB

from .models import Address, Order, User

_db: Optional[SQLerDB] = None


def init_db(path: str | None = None):
    global _db
    if _db is not None:
        return _db
    _db = SQLerDB.on_disk(path) if path else SQLerDB.in_memory(shared=False)

    User.set_db(_db)
    Address.set_db(_db)
    Order.set_db(_db)

    User.ensure_index("age")
    User.ensure_index("address._id")
    Address.ensure_index("city")
    Order.ensure_index("total")

    return _db


def get_db() -> SQLerDB:
    if _db is None:
        raise RuntimeError("DB not initialized. Did you forget to start the app with lifespan?")
    return _db


def close_db() -> None:
    global _db
    if _db is not None:
        _db.close()
        _db = None
