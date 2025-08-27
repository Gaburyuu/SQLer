from __future__ import annotations

from typing import Optional, Type, TypeVar

from pydantic import PrivateAttr

from .async_model import AsyncSQLerModel

TASafe = TypeVar("TASafe", bound="AsyncSQLerSafeModel")


class AsyncSQLerSafeModel(AsyncSQLerModel):
    """Async model with optimistic locking via ``_version`` column."""

    _version: int = PrivateAttr(default=0)

    @classmethod
    def set_db(cls, db, table: Optional[str] = None) -> None:  # type: ignore[override]
        super().set_db(db, table)
        # ensure versioned schema
        # db is AsyncSQLerDB
        # we cannot await here; users should ensure schema via an async helper, or we
        # leave it to first save/refresh paths which call versioned helpers
        # For explicitness, no-op here; version checks happen on use.

    @classmethod
    async def from_id(cls: Type[TASafe], id_: int) -> Optional[TASafe]:  # type: ignore[override]
        db, table = cls._require_binding()
        doc = await db.find_document_with_version(table, id_)
        if doc is None:
            return None
        inst = cls.model_validate(doc)  # type: ignore[call-arg]
        inst._id = doc.get("_id")
        inst._version = doc.get("_version", 0)
        return inst  # type: ignore[return-value]

    async def save(self: TASafe) -> TASafe:  # type: ignore[override]
        cls = self.__class__
        db, table = cls._require_binding()
        payload = self.model_dump(exclude={"_id"})
        try:
            new_id, new_version = await db.upsert_with_version(
                table, self._id, payload, self._version
            )
        except RuntimeError as e:
            from .safe import StaleVersionError  # reuse sync error type for API parity

            raise StaleVersionError(str(e)) from e
        self._id = new_id
        self._version = new_version
        return self

    async def refresh(self: TASafe) -> TASafe:  # type: ignore[override]
        cls = self.__class__
        db, table = cls._require_binding()
        if self._id is None:
            raise ValueError("Cannot refresh unsaved model (missing _id)")
        doc = await db.find_document_with_version(table, self._id)
        if doc is None:
            raise LookupError(f"Row {self._id} not found for refresh")
        fresh = cls.model_validate(doc)  # type: ignore[call-arg]
        for fname in self.__class__.model_fields:
            if fname == "_id":
                continue
            setattr(self, fname, getattr(fresh, fname))
        self._id = doc.get("_id")
        self._version = doc.get("_version", 0)
        return self
