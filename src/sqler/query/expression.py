from typing import Any, Optional, Self


class SQLerExpression:
    """sql expression fragment with parameters; supports & for and, | for or, ~ for not"""

    def __init__(self, sql: str, params: Optional[list[Any]] = None):
        """init with sql fragment and param list; sql like "foo > ?" or "json_extract(data, '$.x') = ?" """
        self.sql = sql
        self.params = params or []

    def __and__(self, other: Self) -> Self:
        """combine two exprs with and; params concatenated"""
        return self.__class__(
            f"({self.sql}) AND ({other.sql})", self.params + other.params
        )
