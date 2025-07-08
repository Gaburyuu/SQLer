from sqler.adapter import SQLiteAdapter
import json
from typing import Any, Optional


class SQLerDB:
    """
    simple, flexible document DB for storing JSON blobs by table
    any table name can be used; you supply the table for each call
    """

    @classmethod
    def in_memory(cls, shared: bool = True) -> "SQLerDB":
        """returns a SQLerDB backed by an in-memory SQLite database"""
        adapter = SQLiteAdapter.in_memory(shared=shared)
        return cls(adapter)

    @classmethod
    def on_disk(cls, path: str = "sqler.db") -> "SQLerDB":
        """returns a SQLerDB using a persistent file on disk"""
        adapter = SQLiteAdapter.on_disk(path)
        return cls(adapter)

    def __init__(self, adapter: SQLiteAdapter):
        self.adapter = adapter
        self.adapter.connect()

    def _ensure_table(self, table: str) -> None:
        """create the target table if it doesn't exist yet"""
        ddl = f"""
        CREATE TABLE IF NOT EXISTS {table} (
            _id INTEGER PRIMARY KEY AUTOINCREMENT,
            data JSON NOT NULL
        );
        """
        self.adapter.execute(ddl)
        self.adapter.commit()

    def insert_document(self, table: str, doc: dict[str, Any]) -> int:
        """insert a document; returns the new _id"""
        self._ensure_table(table)
        payload = json.dumps(doc)
        cursor = self.adapter.execute(
            f"INSERT INTO {table} (data) VALUES (json(?));", [payload]
        )
        self.adapter.commit()
        return cursor.lastrowid

    def upsert_document(
        self, table: str, _id: Optional[int], doc: dict[str, Any]
    ) -> int:
        """insert if new, update if _id exists; returns the _id"""
        self._ensure_table(table)
        payload = json.dumps(doc)
        if _id is None:
            return self.insert_document(table, doc)
        self.adapter.execute(
            f"UPDATE {table} SET data = json(?) WHERE _id = ?;", [payload, _id]
        )
        self.adapter.commit()
        return _id

    def bulk_upsert(self, table: str, docs: list[dict[str, Any]]) -> list[int]:
        """upserts a bunch of docs; assigns _id for new ones"""
        self._ensure_table(table)
        params = []
        new_docs = []

        for doc in docs:
            doc_id = doc.get("_id")
            payload_dict = {k: v for k, v in doc.items() if k != "_id"}
            payload = json.dumps(payload_dict)
            if doc_id is None:
                params.append((None, payload))
                new_docs.append(doc)
            else:
                params.append((doc_id, payload))

        query = f"""
            INSERT INTO {table} (_id, data)
            VALUES (?, json(?))
            ON CONFLICT(_id) DO UPDATE SET data = excluded.data
        """

        with self.adapter as adp:
            cursor = adp.execute(f"SELECT COALESCE(MAX(_id), 0) FROM {table};")
            max_id_before = cursor.fetchone()[0]
            adp.executemany(query, params)
            cursor = adp.execute(f"SELECT MAX(_id) FROM {table};")
            max_id_after = cursor.fetchone()[0]

        if new_docs:
            expected_new = max_id_after - max_id_before
            assert expected_new == len(new_docs), "Mismatch in _id assignment count"
            for doc, new_id in zip(
                new_docs, range(max_id_before + 1, max_id_after + 1)
            ):
                doc["_id"] = new_id

        return [doc.get("_id") for doc in docs]

    def find_document(self, table: str, _id: int) -> Optional[dict[str, Any]]:
        """fetch one document by _id, or None"""
        self._ensure_table(table)
        cur = self.adapter.execute(
            f"SELECT _id, data FROM {table} WHERE _id = ?;", [_id]
        )
        row = cur.fetchone()
        if not row:
            return None
        obj = json.loads(row[1])
        obj["_id"] = row[0]
        return obj

    def delete_document(self, table: str, _id: int) -> None:
        """delete a document by its _id"""
        self._ensure_table(table)
        self.adapter.execute(f"DELETE FROM {table} WHERE _id = ?;", [_id])
        self.adapter.commit()

    def execute_sql(
        self, query: str, params: Optional[list[Any]] = None
    ) -> list[dict[str, Any]]:
        """
        run custom SQL and return a list of JSON documents (dicts)
        the sql statement must be a select that returns a list of docs
            for raw sql perhaps try accessing this obj's adapter
        expects result rows as (_id, data JSON)
        """
        cursor = self.adapter.execute(query, params or [])
        rows = cursor.fetchall()
        docs = []
        for row in rows:
            obj = json.loads(row[1])
            obj["_id"] = row[0]
            docs.append(obj)
        return docs

    def close(self):
        """close the adapter connection"""
        self.adapter.close()

    def connect(self):
        """connect if not already connected"""
        self.adapter.connect()

    def create_index(
        self,
        table: str,
        field: str,
        unique: bool = False,
        name: Optional[str] = None,
        where: Optional[str] = None,
    ):
        """
        create an index on a field (JSON path supported).
        """
        self._ensure_table(table)
        idx_name = name or f"idx_{table}_{field.replace('.', '_')}"
        unique_sql = "UNIQUE" if unique else ""
        expr = (
            f"json_extract(data, '$.{field}')" if not field.startswith("_") else field
        )
        where_sql = f"WHERE {where}" if where else ""
        ddl = f"CREATE {unique_sql} INDEX IF NOT EXISTS {idx_name} ON {table} ({expr}) {where_sql};"
        self.adapter.execute(ddl)
        self.adapter.commit()

    def drop_index(self, name: str):
        """Drop an index by name."""
        ddl = f"DROP INDEX IF EXISTS {name};"
        self.adapter.execute(ddl)
        self.adapter.commit()
