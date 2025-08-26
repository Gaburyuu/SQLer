from __future__ import annotations

from typing import Any, ClassVar, Optional, Type, TypeVar
from pydantic import BaseModel, PrivateAttr

from sqler.db.sqler_db import SQLerDB
from sqler.models.queryset import SQLerQuerySet
from sqler.query import SQLerQuery, SQLerExpression


TModel = TypeVar("TModel", bound="SQLerModel")


def _default_table_name(name: str) -> str:
    return name.lower() + "s"


class SQLerModel(BaseModel):
    """Pydantic-based model with persistence helpers for SQLerDB.

    Define subclasses to model your domain. Bind the class to a database via
    :meth:`set_db`, optionally overriding the table name. Instances persist as
    JSON (excluding the private ``_id`` attribute) into a table with schema
    ``(_id INTEGER PRIMARY KEY AUTOINCREMENT, data JSON NOT NULL)``.
    """

    # internal id stored outside the JSON blob
    _id: Optional[int] = PrivateAttr(default=None)

    # class-bound db + table metadata
    _db: ClassVar[Optional[SQLerDB]] = None
    _table: ClassVar[Optional[str]] = None

    # ----- class config -----
    model_config = {
        "extra": "ignore",
        "frozen": False,
    }

    # ----- class methods -----
    @classmethod
    def set_db(cls: Type[TModel], db: SQLerDB, table: Optional[str] = None) -> None:
        """Bind this model class to a database and table.

        Args:
            db: Database instance to use for persistence.
            table: Optional table name. Defaults to lowercase plural of the
                class name (e.g., ``User`` → ``users``).
        """
        cls._db = db
        cls._table = table or _default_table_name(cls.__name__)
        cls._db._ensure_table(cls._table)

    @classmethod
    def _require_binding(cls) -> tuple[SQLerDB, str]:
        """Return the bound DB and table or raise if unbound.

        Raises:
            RuntimeError: If :meth:`set_db` has not been called.
        """
        if cls._db is None or cls._table is None:
            raise RuntimeError("Model is not bound. Call set_db(db, table?) first.")
        return cls._db, cls._table

    @classmethod
    def from_id(cls: Type[TModel], id_: int) -> Optional[TModel]:
        """Hydrate an instance by ``_id``.

        Args:
            id_: Row id to load.

        Returns:
            Model instance when found, else ``None``.
        """
        db, table = cls._require_binding()
        doc = db.find_document(table, id_)
        if doc is None:
            return None
        inst = cls.model_validate(doc)  # type: ignore[call-arg]
        # attach db id stored outside the json payload
        inst._id = doc.get("_id")
        return inst  # type: ignore[return-value]

    @classmethod
    def query(cls: Type[TModel]) -> SQLerQuerySet[TModel]:
        """Return a queryset for chaining and execution."""
        db, table = cls._require_binding()
        q = db.query(table)
        return SQLerQuerySet[TModel](cls, q)

    @classmethod
    def filter(cls: Type[TModel], expression: SQLerExpression) -> SQLerQuerySet[TModel]:
        """Shorthand for ``cls.query().filter(expression)``."""
        return cls.query().filter(expression)

    @classmethod
    def add_index(
        cls,
        field: str,
        *,
        unique: bool = False,
        name: Optional[str] = None,
        where: Optional[str] = None,
    ) -> None:
        """Create an index on a JSON field via the model class.

        Args:
            field: Dotted JSON path or literal column.
            unique: Enforce uniqueness.
            name: Optional index name.
            where: Optional partial-index WHERE clause.
        """
        db, table = cls._require_binding()
        db.create_index(table, field, unique=unique, name=name, where=where)

    # ----- instance methods -----
    def save(self: TModel) -> TModel:
        """Insert or update this instance and update ``_id``.

        Returns:
            self: The same instance (for chaining).
        """
        cls = self.__class__
        db, table = cls._require_binding()
        payload = self.model_dump(exclude={"_id"})
        new_id = db.upsert_document(table, self._id, payload)
        self._id = new_id
        return self

    def delete(self) -> None:
        """Delete this instance by ``_id`` and unset it.

        Raises:
            ValueError: If the instance has not been saved.
        """
        cls = self.__class__
        db, table = cls._require_binding()
        if self._id is None:
            raise ValueError("Cannot delete unsaved model (missing _id)")
        db.delete_document(table, self._id)
        self._id = None

    def refresh(self: TModel) -> TModel:
        """Reload this instance's fields from the database.

        Raises:
            ValueError: If the instance has not been saved.
            LookupError: If the row no longer exists.

        Returns:
            self: The same instance (for chaining).
        """
        cls = self.__class__
        db, table = cls._require_binding()
        if self._id is None:
            raise ValueError("Cannot refresh unsaved model (missing _id)")
        doc = db.find_document(table, self._id)
        if doc is None:
            raise LookupError(f"Row {self._id} not found for refresh")
        fresh = cls.model_validate(doc)  # type: ignore[call-arg]
        # update fields in-place (excluding _id which is also present)
        for fname in self.__class__.model_fields:
            if fname == "_id":
                continue
            setattr(self, fname, getattr(fresh, fname))
        # set db id explicitly
        self._id = doc.get("_id")
        return self
