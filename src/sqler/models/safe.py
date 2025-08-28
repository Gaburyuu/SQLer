from __future__ import annotations

from typing import Optional, Type, TypeVar
import time
import sqlite3

from pydantic import PrivateAttr

from .model import SQLerModel
from .queryset import SQLerQuerySet


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

    @classmethod
    def query(cls: Type[TSafe]) -> SQLerQuerySet[TSafe]:  # type: ignore[override]
        qs = super().query()  # base queryset
        # For perf runs, include _version when materializing
        import os
        if os.environ.get("SQLER_QUERY_INCLUDE_VERSION", "").lower() in {"1", "true", "yes"}:
            return _SafeSQLerQuerySet(cls, qs._query)  # type: ignore[arg-type]
        return qs  # type: ignore[return-value]


class _SafeSQLerQuerySet(SQLerQuerySet[TSafe]):
    def first(self) -> Optional[TSafe]:  # type: ignore[override]
        inst = super().first()
        if inst is None:
            return None
        # Rehydrate with version for correctness under contention
        cls = self._model_cls  # type: ignore[attr-defined]
        try:
            fresh = cls.from_id(inst._id)  # type: ignore[attr-defined]
            return fresh if fresh is not None else inst
        except Exception:
            return inst

    def save(self: TSafe) -> TSafe:  # type: ignore[override]
        """Insert or update with optimistic locking.

        Raises:
            StaleVersionError: On version mismatch during update.
        """
        cls = self.__class__
        db, table = cls._require_binding()
        payload = self._dump_with_relations()
        # Optional JIT version fetch for perf/concurrency stress mode
        import os as _os
        if self._id is not None and _os.environ.get("SQLER_JIT_VERSION", "").lower() in {"1", "true", "yes"}:
            latest0 = cls.from_id(self._id)
            if latest0 is not None:
                self._version = latest0._version
        # small retry loop for hot contention and transient locks
        max_retries = 128
        for attempt in range(max_retries):
            try:
                new_id, new_version = db.upsert_with_version(
                    table, self._id, payload, self._version
                )
                self._id = new_id
                self._version = new_version
                return self
            except sqlite3.OperationalError as e:
                if "locked" in str(e).lower():
                    time.sleep(0.005 * (attempt + 1))
                    continue
                raise
            except RuntimeError as e:
                # Stale version conflict
                import os as _os
                if _os.environ.get("SQLER_RETRY_ON_STALE", "").lower() in {"1", "true", "yes"}:
                    latest = cls.from_id(self._id) if self._id is not None else None
                    if latest is None:
                        from .safe import StaleVersionError as _SVE
                        raise _SVE(str(e)) from e
                    # best-effort merge for numeric deltas based on snapshot
                    try:
                        base = getattr(self, "_snapshot", None)
                        if isinstance(base, dict):
                            for key, self_val in list(self.__dict__.items()):
                                if key.startswith("_"):
                                    continue
                                base_val = base.get(key)
                                latest_val = getattr(latest, key, None)
                                if isinstance(self_val, int) and isinstance(base_val, int) and isinstance(latest_val, int):
                                    delta = self_val - base_val
                                    setattr(self, key, latest_val + delta)
                    except Exception:
                        pass
                    self._version = latest._version
                    time.sleep(0.001 * (attempt + 1))
                    # recompute payload with merged value and retry
                    payload = self._dump_with_relations()
                    # update snapshot to latest for subsequent merges
                    try:
                        self._snapshot = latest.model_dump()  # type: ignore[attr-defined]
                    except Exception:
                        pass
                    continue
                # surface to caller to re-fetch and retry
                from .safe import StaleVersionError as _SVE  # local alias
                raise _SVE(str(e)) from e
        # exhausted
        raise StaleVersionError("save retries exhausted")

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
