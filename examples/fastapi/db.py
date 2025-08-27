from sqler import SQLerDB
from .models import User, Address, Order

_db = None


def init_db(path: str | None = None):
    global _db
    if _db is not None:
        return _db
    _db = SQLerDB.on_disk(path) if path else SQLerDB.in_memory(shared=False)
    User.set_db(_db)
    Address.set_db(_db)
    Order.set_db(_db)
    # helpful indices
    User.ensure_index("age")
    User.ensure_index("address._id")
    Address.ensure_index("city")
    Order.ensure_index("total")
    return _db


def get_db():
    return _db


def close_db():
    global _db
    if _db:
        _db.close()
        _db = None

