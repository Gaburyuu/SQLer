from __future__ import annotations

from typing import Any, Generic, Optional, Type, TypeVar
from sqler.query.async_query import AsyncSQLerQuery
from sqler.query import SQLerExpression


T = TypeVar("T")


class AsyncSQLerQuerySet(Generic[T]):
    """Async queryset that materializes model instances."""

    def __init__(self, model_cls: Type[T], query: AsyncSQLerQuery) -> None:
        self._model_cls = model_cls
        self._query = query
        self._resolve = True

    def resolve(self, flag: bool) -> "AsyncSQLerQuerySet[T]":
        clone = self.__class__(self._model_cls, self._query)
        clone._resolve = flag
        return clone

    # chaining
    def filter(self, expression: SQLerExpression) -> "AsyncSQLerQuerySet[T]":
        return self.__class__(self._model_cls, self._query.filter(expression))

    def exclude(self, expression: SQLerExpression) -> "AsyncSQLerQuerySet[T]":
        return self.__class__(self._model_cls, self._query.exclude(expression))

    def order_by(self, field: str, desc: bool = False) -> "AsyncSQLerQuerySet[T]":
        return self.__class__(self._model_cls, self._query.order_by(field, desc))

    def limit(self, n: int) -> "AsyncSQLerQuerySet[T]":
        return self.__class__(self._model_cls, self._query.limit(n))

    # execution
    async def all(self) -> list[T]:
        docs = await self._query.all_dicts()
        results: list[T] = []
        for d in docs:
            if self._resolve:
                try:
                    aresolver = getattr(self._model_cls, "_aresolve_relations")
                    d = await aresolver(d)  # type: ignore[assignment]
                except Exception:
                    pass
            inst = self._model_cls.model_validate(d)  # type: ignore[attr-defined]
            try:
                inst._id = d.get("_id")  # type: ignore[attr-defined]
            except Exception:
                pass
            results.append(inst)
        return results

    async def first(self) -> Optional[T]:
        d = await self._query.first_dict()
        if d is None:
            return None
        if self._resolve:
            try:
                aresolver = getattr(self._model_cls, "_aresolve_relations")
                d = await aresolver(d)  # type: ignore[assignment]
            except Exception:
                pass
        inst = self._model_cls.model_validate(d)  # type: ignore[attr-defined]
        try:
            inst._id = d.get("_id")  # type: ignore[attr-defined]
        except Exception:
            pass
        return inst

    async def count(self) -> int:
        return await self._query.count()

    # inspection
    def sql(self) -> str:
        return self._query.sql

    def params(self) -> list[Any]:
        return self._query.params
