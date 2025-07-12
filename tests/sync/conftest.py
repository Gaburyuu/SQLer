import pytest
from sqler import SQLiteAdapter, SQLerDB


@pytest.fixture(scope="function")
def oligo_adapter():
    adapter = SQLiteAdapter.in_memory(shared=False)
    adapter.connect()

    adapter.execute("""
        CREATE TABLE oligos (
            length INTEGER,
            sequence STRING
        );
    """)

    yield adapter

    adapter.close()


@pytest.fixture(scope="function")
def oligo_db():
    db = SQLerDB.in_memory(shared=False)
    table = "oligos"
    db._ensure_table(table=table)

    yield db

    db.close()
