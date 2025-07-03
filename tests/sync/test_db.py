import pytest
from sqler.db import DBABC, SQLiteDB


def tests_run_at_all():
    assert True


@pytest.fixture(params=["memory", "disk"])
def db(request, tmp_path):
    """yields a connected db in memory and on disk"""
    path = request.__type_params__
    if path == "disk":
        path = str(tmp_path / "test.db")
    else:
        path = ":memory:"

    db = SQLiteDB(path)
    db.connect()
    yield db
    db.close()


def test_db_implements_abc():
    """verify the inheritance is cool"""
    assert issubclass(SQLiteDB, DBABC)
