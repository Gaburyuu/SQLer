from typing import Any, Optional, Self
from .expression import SQLerExpression
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

    def _build_query(self) -> tuple[str, list[Any]]:
        """builds the select statement and param list"""
        where = f"WHERE {self._expression.sql}" if self._expression else ""
        order = ""
        if self._order:
            order = f"ORDER BY json_extract(data, '$.{self._order}')" + (
                " DESC" if self._desc else ""
            )
        limit = f"LIMIT {self._limit}" if self._limit is not None else ""
        sql = f"SELECT data FROM {self._table} {where} {order} {limit}".strip()
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
            NoAdapterError("No adapter set for query")
        sql, params = self._build_query()
        cur = self._adapter.execute(sql, params)
        return [cur for cur in cur.fetchall()]

    def first(self) -> Optional[dict[str, Any]]:
        """runs the query limited to 1; returns first doc or none"""
        if self._adapter is None:
            NoAdapterError("No adapter set for query")
        return self.limit(1).all()[0] if self.limit(1).all() else None

    def count(self) -> int:
        """returns count of matching oligos"""
        if self._adapter is None:
            NoAdapterError("No adapter set for query")
        sql, params = self._build_query()
        count_sql = sql.replace("SELECT data", "SELECT count(*)")
        cur = self._adapter.execute(count_sql, params)
        row = cur.fetchone()
        return int(row[0]) if row else 0
