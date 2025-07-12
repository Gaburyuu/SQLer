from typing import Any, Optional, Self
from .expression import SQLerExpression


class SQLerQuery:
    """turns expression fragments into sql"""

    def __init__(self, table: str, expression: Optional[SQLerExpression] = None):
        """can init with an expression"""
        self._table = table
        self._expression = expression

    def filter(self, expression: SQLerExpression) -> Self:
        """returns a new query obj w/ the expression added as a filter"""
        new_expression = (
            expression if self._expression is None else (self._expression & expression)
        )
        return self.__class__(table=self._table, expression=new_expression)

    def _build_query(self) -> tuple[str, list[Optional[Any]]]:
        """builds the current exprssions into real life sql"""

        # if we don't have conditions then we just don't filter
        if self._expression:
            where_sql = f"WHERE {self._expression.sql}"
        else:
            where_sql = ""
        # connect the expression into a select where statement
        sql = f"SELECT data FROM {self._table} {where_sql}".strip()
        return (sql, self.params)

    @property
    def sql(self) -> str:
        """returns the sql that will be run"""
        return self._build_query()[0]

    @property
    def params(self) -> list[Optional[Any]]:
        """returns the current params"""
        if self._expression:
            return self._expression.params
        else:
            return []
