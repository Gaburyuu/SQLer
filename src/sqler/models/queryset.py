from __future__ import annotations

from typing import Any, Generic, Optional, Type, TypeVar
from sqler.query import SQLerQuery, SQLerExpression


T = TypeVar("T")


class SQLerQuerySet(Generic[T]):
    """A thin wrapper around SQLerQuery that materializes model instances."""

    def __init__(
        self,
        model_cls: Type[T],
        query: SQLerQuery,
    ) -> None:
        self._model_cls = model_cls
        self._query = query

    # chaining returns new wrappers
    def filter(self, expression: SQLerExpression) -> "SQLerQuerySet[T]":
        return self.__class__(self._model_cls, self._query.filter(expression))

    def exclude(self, expression: SQLerExpression) -> "SQLerQuerySet[T]":
        return self.__class__(self._model_cls, self._query.exclude(expression))

    def order_by(self, field: str, desc: bool = False) -> "SQLerQuerySet[T]":
        return self.__class__(self._model_cls, self._query.order_by(field, desc))

    def limit(self, n: int) -> "SQLerQuerySet[T]":
        return self.__class__(self._model_cls, self._query.limit(n))

    # execution
    def all(self) -> list[T]:
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
        return self._query.count()

    # inspection
    def sql(self) -> str:
        return self._query.sql

    def params(self) -> list[Any]:
        return self._query.params
