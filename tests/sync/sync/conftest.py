import pytest
from sqler import SQLiteDB


@pytest.fixture(scope="function")
def oligo_table():
    db = SQLiteDB.in_memory(shared=False)
    db.connect()

    db.execute("""
        CREATE TABLE oligos (
            length INTEGER,
            sequence STRING
        );
    """)

    yield db

    db.close()
