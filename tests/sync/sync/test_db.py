import pytest
from sqler.db import DBABC, SQLiteDB, NotConnectedError
from sqlite3 import ProgrammingError, OperationalError


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


def test_executescript(oligo_table):
    """test multiline scripts"""
    script = """
    INSERT INTO oligos(length) VALUES (1), (2);
    INSERT INTO oligos(length) VALUES (3);
    """
    oligo_table.executescript(script)

    # this part should fail
    with pytest.raises(ProgrammingError):
        oligo_table.execute(script)

    cur = oligo_table.execute("SELECT length FROM oligos ORDER BY length;")
    assert [row[0] for row in cur.fetchall()] == [1, 2, 3]


def test_context_manager(tmp_path):
    """test context manager commit"""
    path = str(tmp_path / "context_manager.db")
    with SQLiteDB(path) as db:
        db.execute("CREATE TABLE cm(x TEXT);")
        db.execute("INSERT INTO cm(x) VALUES (?);", ["hi"])
        db.commit()
        cur = db.execute("SELECT x FROM cm;")
        assert cur.fetchone()[0] == "hi"


def test_close_then_error(oligo_table):
    """ensure close disables operations"""
    oligo_table.close()
    with pytest.raises(NotConnectedError):
        oligo_table.execute("SELECT 1;")
    with pytest.raises(NotConnectedError):
        oligo_table.commit()
    with pytest.raises(NotConnectedError):
        oligo_table.executemany("SELECT 1;", [])


def test_execute_invalid_sql(oligo_table):
    """invalid sql raises OperationalError"""
    with pytest.raises(OperationalError):
        oligo_table.execute("THIS IS NOT VALID SQL")


def test_executemany_empty_list(oligo_table):
    """executemany with empty list should do nothing, not error"""
    oligo_table.execute("CREATE TABLE test_empty(x INTEGER);")
    oligo_table.executemany("INSERT INTO test_empty(x) VALUES (?);", [])
    cur = oligo_table.execute("SELECT COUNT(*) FROM test_empty;")
    assert cur.fetchone()[0] == 0


def test_commit_without_connection():
    """commit before connect should error"""
    db = SQLiteDB(":memory:")
    with pytest.raises(NotConnectedError):
        db.commit()


def test_multiple_connects_and_closes(tmp_path):
    """connect/close multiple times, then ensure closed disables executes"""
    path = str(tmp_path / "multi.db")
    db = SQLiteDB(path)
    db.connect()
    db.connect()
    db.close()
    db.close()
    with pytest.raises(NotConnectedError):
        db.execute("SELECT 1;")


def test_context_manager_rollback_on_exception(tmp_path):
    """rollback on exception: should not commit inserts"""
    path = str(tmp_path / "cm_rollback.db")
    try:
        with SQLiteDB(path) as db:
            db.execute("CREATE TABLE foo(x INTEGER);")
            db.execute("INSERT INTO foo(x) VALUES (1);")
            raise RuntimeError("Force rollback")
    except RuntimeError:
        pass
    # Data should NOT be committed if rollback works right
    db2 = SQLiteDB(path)
    db2.connect()
    cur = db2.execute("SELECT COUNT(*) FROM foo;")
    assert cur.fetchone()[0] == 0
