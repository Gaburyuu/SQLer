from sqler import SQLerDB, SQLiteAdapter


def test_sqlerdb_imports():
    assert SQLerDB is not None


def test_create_and_init():
    db = SQLerDB(adapter=SQLiteAdapter.on_disk())
    db._ensure_table("documents")


def test_factories():
    # tests if the factories work
    mem = SQLerDB.in_memory(shared=False)
    disk = SQLerDB.on_disk()
    for db in [mem, disk]:
        assert isinstance(db, SQLerDB)


def test_insert_and_find(oligo_db):
    doc = {"length": 4, "sequence": "ACGT"}
    table = "oligos"
    doc_id = oligo_db.insert_document(table, doc)
    assert isinstance(doc_id, int)
    result = oligo_db.find_document(table, doc_id)
    assert result["length"] == 4
    assert result["sequence"] == "ACGT"
    assert result["_id"] == doc_id
