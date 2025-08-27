from __future__ import annotations

from typing import Optional, Type, TypeVar, ClassVar
from pydantic import BaseModel, PrivateAttr

from sqler.db.async_db import AsyncSQLerDB
from sqler.query.async_query import AsyncSQLerQuery
from sqler.models.async_queryset import AsyncSQLerQuerySet
from sqler.query import SQLerExpression


TAModel = TypeVar("TAModel", bound="AsyncSQLerModel")


class AsyncSQLerModel(BaseModel):
    """Async Pydantic-based model with persistence helpers."""

    _id: Optional[int] = PrivateAttr(default=None)
    _db: ClassVar[Optional[AsyncSQLerDB]] = None
    _table: ClassVar[Optional[str]] = None

    model_config = {"extra": "ignore"}

    @classmethod
    def set_db(cls, db: AsyncSQLerDB, table: Optional[str] = None) -> None:
        cls._db = db
        cls._table = table or cls.__name__.lower() + "s"

    @classmethod
    def _require_binding(cls) -> tuple[AsyncSQLerDB, str]:
        if cls._db is None or cls._table is None:
            raise RuntimeError("Model is not bound. Call set_db(db, table?) first.")
        return cls._db, cls._table

    @classmethod
    async def from_id(cls: Type[TAModel], id_: int) -> Optional[TAModel]:
        db, table = cls._require_binding()
        doc = await db.find_document(table, id_)
        if doc is None:
            return None
        inst = cls.model_validate(doc)
        inst._id = doc.get("_id")
        return inst  # type: ignore[return-value]

    @classmethod
    def query(cls: Type[TAModel]) -> AsyncSQLerQuerySet[TAModel]:
        db, table = cls._require_binding()
        q = AsyncSQLerQuery(table=table, adapter=db.adapter)
        return AsyncSQLerQuerySet[TAModel](cls, q)

    @classmethod
    def filter(cls: Type[TAModel], expression: SQLerExpression) -> AsyncSQLerQuerySet[TAModel]:
        return cls.query().filter(expression)

    async def save(self: TAModel) -> TAModel:
        cls = self.__class__
        db, table = cls._require_binding()
        payload = self.model_dump(exclude={"_id"})
        new_id = await db.upsert_document(table, self._id, payload)
        self._id = new_id
        return self

    async def delete(self) -> None:
        cls = self.__class__
        db, table = cls._require_binding()
        if self._id is None:
            raise ValueError("Cannot delete unsaved model (missing _id)")
        # reuse execute directly for delete to keep API small
        await db.adapter.execute(f"DELETE FROM {table} WHERE _id = ?;", [self._id])
        await db.adapter.commit()
        self._id = None

    async def refresh(self: TAModel) -> TAModel:
        cls = self.__class__
        db, table = cls._require_binding()
        if self._id is None:
            raise ValueError("Cannot refresh unsaved model (missing _id)")
        doc = await db.find_document(table, self._id)
        if doc is None:
            raise LookupError(f"Row {self._id} not found for refresh")
        fresh = cls.model_validate(doc)
        for fname in self.__class__.model_fields:
            if fname == "_id":
                continue
            setattr(self, fname, getattr(fresh, fname))
        self._id = doc.get("_id")
        return self
