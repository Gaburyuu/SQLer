from __future__ import annotations

from typing import Any, Generic, Optional, Type, TypeVar
from sqler.query import SQLerQuery, SQLerExpression


T = TypeVar("T")


class SQLerQuerySet(Generic[T]):
    """Query wrapper that materializes model instances.

    This class wraps a :class:`~sqler.query.query.SQLerQuery` and converts
    results into instances of the bound Pydantic model class.
    """

    def __init__(
        self,
        model_cls: Type[T],
        query: SQLerQuery,
    ) -> None:
        self._model_cls = model_cls
        self._query = query

    # chaining returns new wrappers
    def filter(self, expression: SQLerExpression) -> "SQLerQuerySet[T]":
        """Return a new queryset filtered by the expression."""
        return self.__class__(self._model_cls, self._query.filter(expression))

    def exclude(self, expression: SQLerExpression) -> "SQLerQuerySet[T]":
        """Return a new queryset excluding rows matching the expression."""
        return self.__class__(self._model_cls, self._query.exclude(expression))

    def order_by(self, field: str, desc: bool = False) -> "SQLerQuerySet[T]":
        """Return a new queryset ordered by the given JSON field."""
        return self.__class__(self._model_cls, self._query.order_by(field, desc))

    def limit(self, n: int) -> "SQLerQuerySet[T]":
        """Return a new queryset with a LIMIT clause."""
        return self.__class__(self._model_cls, self._query.limit(n))

    # execution
    def all(self) -> list[T]:
        """Execute and return a list of model instances."""
        docs = self._query.all_dicts()
        results: list[T] = []
        for d in docs:
            inst = self._model_cls.model_validate(d)  # type: ignore[attr-defined]
            # attach db id if present but excluded from schema
            try:
                inst._id = d.get("_id")  # type: ignore[attr-defined]
            except Exception:
                pass
            results.append(inst)
        return results

    def first(self) -> Optional[T]:
        """Execute with LIMIT 1 and return the first model instance, if any."""
        d = self._query.first_dict()
        if d is None:
            return None
        inst = self._model_cls.model_validate(d)  # type: ignore[attr-defined]
        try:
            inst._id = d.get("_id")  # type: ignore[attr-defined]
        except Exception:
            pass
        return inst

    def count(self) -> int:
        """Return the count of matching rows."""
        return self._query.count()

    # inspection
    def sql(self) -> str:
        """Return the underlying SELECT SQL string."""
        return self._query.sql

    def params(self) -> list[Any]:
        """Return the underlying parameter list."""
        return self._query.params
