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


def test_factories():
    """makes sure the factory funcs work"""
    mem_db = SQLiteDB.in_memory()
    mem_db.connect()
    disk_db = SQLiteDB.in_memory()
    disk_db.connect()
    for db in [mem_db, disk_db]:
        cursor = db.execute("PRAGMA user_version;")
        assert isinstance(cursor.fetchone()[0], int)


def test_execute_and_commit(oligo_table):
    """tests basic execution"""
    oligo_table.execute("INSERT INTO oligos (length) VALUES (?);", [100])
    oligo_table.commit()
    cursor = oligo_table.execute("SELECT length FROM oligos;")
    assert cursor.fetchone()[0] == 100


def test_executemany_batch_insert(oligo_table):
    """tests execute many"""
    values = [[i] for i in range(100)]
    oligo_table.executemany("INSERT INTO oligos(length) VALUES (?);", values)
    cursor = oligo_table.execute("SELECT COUNT(*) FROM oligos;")
    assert cursor.fetchone()[0] == 100
