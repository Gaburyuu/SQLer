import json
from typing import Any, Optional

from sqler.adapter.asynchronous import AsyncSQLiteAdapter


class AsyncSQLerDB:
    """Async document store for JSON blobs on SQLite."""

    @classmethod
    def in_memory(cls, shared: bool = True) -> "AsyncSQLerDB":
        adapter = AsyncSQLiteAdapter.in_memory(shared=shared)
        return cls(adapter)

    @classmethod
    def on_disk(cls, path: str = "sqler.db") -> "AsyncSQLerDB":
        adapter = AsyncSQLiteAdapter.on_disk(path)
        return cls(adapter)

    def __init__(self, adapter: AsyncSQLiteAdapter):
        self.adapter = adapter

    async def connect(self) -> None:
        await self.adapter.connect()

    async def close(self) -> None:
        await self.adapter.close()

    async def _ensure_table(self, table: str) -> None:
        ddl = f"""
        CREATE TABLE IF NOT EXISTS {table} (
            _id INTEGER PRIMARY KEY AUTOINCREMENT,
            data JSON NOT NULL
        );
        """
        await self.adapter.execute(ddl)
        await self.adapter.commit()

    async def insert_document(self, table: str, doc: dict[str, Any]) -> int:
        await self._ensure_table(table)
        payload = json.dumps(doc)
        cur = await self.adapter.execute(
            f"INSERT INTO {table} (data) VALUES (json(?));", [payload]
        )
        await self.adapter.commit()
        return cur.lastrowid  # type: ignore[attr-defined]

    async def upsert_document(self, table: str, _id: Optional[int], doc: dict[str, Any]) -> int:
        await self._ensure_table(table)
        payload = json.dumps(doc)
        if _id is None:
            return await self.insert_document(table, doc)
        await self.adapter.execute(
            f"UPDATE {table} SET data = json(?) WHERE _id = ?;", [payload, _id]
        )
        await self.adapter.commit()
        return _id

    async def find_document(self, table: str, _id: int) -> Optional[dict[str, Any]]:
        await self._ensure_table(table)
        cur = await self.adapter.execute(f"SELECT _id, data FROM {table} WHERE _id = ?;", [_id])
        row = await cur.fetchone()
        if not row:
            return None
        obj = json.loads(row[1])
        obj["_id"] = row[0]
        return obj

