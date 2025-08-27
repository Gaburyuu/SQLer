from __future__ import annotations

from typing import Optional, Type, TypeVar

from pydantic import PrivateAttr

from .model import SQLerModel


class StaleVersionError(RuntimeError):
    """Raised when saving a model with a stale version."""


TSafe = TypeVar("TSafe", bound="SQLerSafeModel")


class SQLerSafeModel(SQLerModel):
    """Model with optimistic locking via a ``_version`` column.

    New rows start at version 0. Updates require the current ``_version`` and
    increment it atomically. Conflicts raise :class:`StaleVersionError`.
    """

    _version: int = PrivateAttr(default=0)

    @classmethod
    def set_db(cls: Type[TSafe], db, table: Optional[str] = None) -> None:  # type: ignore[override]
        """Bind the model to a DB and ensure the versioned schema.

        Adds a ``_version`` column to the table if missing.
        """
        super().set_db(db, table)
        # upgrade table to versioned
        db._ensure_versioned_table(cls._table)  # type: ignore[arg-type]

    @classmethod
    def from_id(cls: Type[TSafe], id_: int) -> Optional[TSafe]:  # type: ignore[override]
        db, table = cls._require_binding()
        doc = db.find_document_with_version(table, id_)
        if doc is None:
            return None
        inst = cls.model_validate(doc)  # type: ignore[call-arg]
        inst._id = doc.get("_id")  # type: ignore[attr-defined]
        inst._version = doc.get("_version", 0)  # type: ignore[attr-defined]
        return inst  # type: ignore[return-value]

    def save(self: TSafe) -> TSafe:  # type: ignore[override]
        """Insert or update with optimistic locking.

        Raises:
            StaleVersionError: On version mismatch during update.
        """
        cls = self.__class__
        db, table = cls._require_binding()
        payload = self._dump_with_relations()
        try:
            new_id, new_version = db.upsert_with_version(table, self._id, payload, self._version)
        except RuntimeError as e:
            raise StaleVersionError(str(e)) from e
        self._id = new_id
        self._version = new_version
        return self

    def refresh(self: TSafe) -> TSafe:  # type: ignore[override]
        cls = self.__class__
        db, table = cls._require_binding()
        if self._id is None:
            raise ValueError("Cannot refresh unsaved model (missing _id)")
        doc = db.find_document_with_version(table, self._id)
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
