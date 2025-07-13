from typing import Any, List, Union
from sqler.query import SQLerExpression


class SQLerField:
    """proxy for a json field; lets you do field == x, field > 5, field["foo"], field / "foo", etc"""

    def __init__(self, path: Union[str, List[str]]):
        """init with a path; path is str or list of path parts like ["meta", "nucleotides"]"""
        if isinstance(path, str):
            self.path = [path]
        else:
            self.path = list(path)

    def __repr__(self):
        return f"SQLerField({self.path!r})"

    def _json_path(self) -> str:
        """
        build a valid sqlite json path string;
        eg ['foo', 'bar', 0, 'baz'] → '$.foo.bar[0].baz';
        ints mean array index, strings mean keys; keys with weird chars get quoted
        """
        import re

        if not self.path:
            return "$"

        def needs_quoting(s: str) -> bool:
            # sqlite json path identifiers: must start with letter/_ and only contain alphanum/_
            return not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", s)

        parts = ["$"]
        for segment in self.path:
            if isinstance(segment, int):
                parts.append(f"[{segment}]")
            else:
                if needs_quoting(segment):
                    escaped = segment.replace('"', '\\"')
                    parts.append(f'."{escaped}"')
                else:
                    parts.append(f".{segment}")
        return "".join(parts)

    def _make_expr(self, op: str, val: Any) -> SQLerExpression:
        """build a SQLerExpression for a comparison: =, !=, >, etc"""
        return SQLerExpression(
            f"JSON_EXTRACT(data, '{self._json_path()}') {op} ?", [val]
        )

    def __eq__(self, other: Any) -> SQLerExpression:
        """field == value"""
        return self._make_expr("=", other)

    def __ne__(self, other: Any) -> SQLerExpression:
        """field != value"""
        return self._make_expr("!=", other)

    def __gt__(self, other: Any) -> SQLerExpression:
        """field > value"""
        return self._make_expr(">", other)

    def __ge__(self, other: Any) -> SQLerExpression:
        """field >= value"""
        return self._make_expr(">=", other)

    def __lt__(self, other: Any) -> SQLerExpression:
        """field < value"""
        return self._make_expr("<", other)

    def __le__(self, other: Any) -> SQLerExpression:
        """field <= value"""
        return self._make_expr("<=", other)

    def __getitem__(self, item: str) -> "SQLerField":
        """field["foo"] goes deeper into json path"""
        return SQLerField(self.path + [item])

    def __truediv__(self, other: str) -> "SQLerField":
        """field / "foo" is an alternative for field["foo"]"""
        return SQLerField(self.path + [other])

    def contains(self, value: Any) -> SQLerExpression:
        """checks if array contains a value"""
        json_path = self._json_path()  # e.g., '$.tags'
        expression = f"EXISTS (SELECT 1 FROM json_each(data, '{json_path}') WHERE json_each.value = ?)"
        return SQLerExpression(expression, [value])

    def isin(self, values: list) -> SQLerExpression:
        """checks if it's in a list of values"""
        if not values:
            # empty IN always false
            return SQLerExpression("0", [])
        json_path = self._json_path()
        placeholders = ", ".join("?" for _ in values)
        expression = f"EXISTS (SELECT 1 FROM json_each(data, '{json_path}') WHERE json_each.value IN ({placeholders}))"
        return SQLerExpression(expression, values)

    def like(self, pattern: str) -> SQLerExpression:
        """field.like('abc%') → field LIKE ?"""
        return SQLerExpression(
            f"JSON_EXTRACT(data, '{self._json_path()}') LIKE ?", [pattern]
        )
