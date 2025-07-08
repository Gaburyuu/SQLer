import pytest
from sqler.db import DBABC, SQLiteDB


def tests_run_at_all():
    assert True


@pytest.fixture(params=[("memory", "in_memory"), ("disk", "on_disk")])
def db(request, tmp_path):
    """yields a connected db in memory and on disk"""
    path = request.param
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
    # also pytest needs any test at all to not fail on github action?
    assert issubclass(SQLiteDB, DBABC)


def test_execute_and_commit(db):
    """tests basic execution"""
    db.execute("CREATE TABLE oligo (length INTEGER);")
    db.execute("INSERT INTO oligo (length) VALUES (?);", [100])
    db.commit()
    cursor = db.execute("SELECT length FROM oligo;")
    assert cursor.fetchone()[0] == 100
