from typing import Any, Optional, Self
from sqler.query import SQLerExpression
from sqler.adapter.abstract import AdapterABC


class QueryError(Exception):
    """Base exception for query errors."""

    pass


class NoAdapterError(ConnectionError):
    """Raised when attempting to execute operations without an adapter set."""

    pass


class SQLerQuery:
    """builds and runs chainable queries"""

    def __init__(
        self,
        table: str,
        adapter: Optional[AdapterABC] = None,
        expression: Optional[SQLerExpression] = None,
        order: Optional[str] = None,
        desc: bool = False,
        limit: Optional[int] = None,
    ):
        self._table = table
        self._adapter = adapter
        self._expression = expression
        self._order = order
        self._desc = desc
        self._limit = limit

    def filter(self, expression: SQLerExpression) -> Self:
        """returns a new query with expression anded in"""
        new_expression = (
            expression if self._expression is None else (self._expression & expression)
        )
        return self.__class__(
            self._table,
            self._adapter,
            new_expression,
            self._order,
            self._desc,
            self._limit,
        )

    def exclude(self, expression: SQLerExpression) -> Self:
        """returns a new query with not-expression anded in"""
        not_expr = ~expression
        new_expression = (
            not_expr if self._expression is None else (self._expression & not_expr)
        )
        return self.__class__(
            self._table,
            self._adapter,
            new_expression,
            self._order,
            self._desc,
            self._limit,
        )

    def order_by(self, field: str, desc: bool = False) -> Self:
        """returns a new query ordered by field"""
        return self.__class__(
            self._table, self._adapter, self._expression, field, desc, self._limit
        )

    def limit(self, n: int) -> Self:
        """returns a new query limited to n results"""
        return self.__class__(
            self._table, self._adapter, self._expression, self._order, self._desc, n
        )

    def _build_query(self, *, include_id: bool = False) -> tuple[str, list[Any]]:
        """builds the select statement and param list

        include_id: when True, selects `_id, data` instead of only `data`.
        """
        where = f"WHERE {self._expression.sql}" if self._expression else ""
        order = ""
        if self._order:
            order = f"ORDER BY json_extract(data, '$.{self._order}')" + (
                " DESC" if self._desc else ""
            )
        limit = f"LIMIT {self._limit}" if self._limit is not None else ""
        select = "_id, data" if include_id else "data"
        sql = f"SELECT {select} FROM {self._table} {where} {order} {limit}".strip()
        sql = " ".join(sql.split())  # collapse double spaces
        params = self._expression.params if self._expression else []
        return sql, params

    @property
    def sql(self) -> str:
        """returns the current select sql"""
        return self._build_query()[0]

    @property
    def params(self) -> list[Any]:
        """returns the current param list"""
        return self._build_query()[1]

    def all(self) -> list[dict[str, Any]]:
        """runs the query; returns all matching oligo docs as dicts"""
        if self._adapter is None:
            raise NoAdapterError("No adapter set for query")
        sql, params = self._build_query()
        cur = self._adapter.execute(sql, params)
        return [row[0] for row in cur.fetchall()]

    def first(self) -> Optional[dict[str, Any]]:
        """runs the query limited to 1; returns first doc or none"""
        if self._adapter is None:
            raise NoAdapterError("No adapter set for query")
        return self.limit(1).all()[0] if self.limit(1).all() else None

    def count(self) -> int:
        """returns count of matching oligos"""
        if self._adapter is None:
            raise NoAdapterError("No adapter set for query")
        sql, params = self._build_query()
        count_sql = sql.replace("SELECT data", "SELECT count(*)")
        cur = self._adapter.execute(count_sql, params)
        row = cur.fetchone()
        return int(row[0]) if row else 0

    def all_dicts(self) -> list[dict[str, Any]]:
        """runs the query; returns list of parsed dicts with `_id` attached"""
        if self._adapter is None:
            raise NoAdapterError("No adapter set for query")
        import json

        sql, params = self._build_query(include_id=True)
        cur = self._adapter.execute(sql, params)
        rows = cur.fetchall()
        docs: list[dict[str, Any]] = []
        for _id, data_json in rows:
            obj = json.loads(data_json)
            obj["_id"] = _id
            docs.append(obj)
        return docs

    def first_dict(self) -> Optional[dict[str, Any]]:
        """runs the query limited to 1; returns first parsed dict (with `_id`) or None"""
        if self._adapter is None:
            raise NoAdapterError("No adapter set for query")
        results = self.limit(1).all_dicts()
        return results[0] if results else None
