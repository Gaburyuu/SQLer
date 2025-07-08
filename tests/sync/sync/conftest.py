import pytest
from sqler import SQLiteAdapter


@pytest.fixture(scope="function")
def oligo_adapter():
    db = SQLiteAdapter.in_memory(shared=False)
    db.connect()

    db.execute("""
        CREATE TABLE oligos (
            length INTEGER,
            sequence STRING
        );
    """)

    yield db

    db.close()
