from __future__ import annotations

from typing import Any, List, Sequence, Union, Type

from sqler.query.expression import SQLerExpression
from sqler.models.model import SQLerModel


class SQLerModelField:
    """Model-aware field that compiles relationship-crossing predicates.

    Example:
      SQLerModelField(User, ["address", "city"]) == "Kyoto"
      -> EXISTS (
           SELECT 1 FROM addresses r
           WHERE r._id = json_extract(data, '$.address._id')
             AND json_extract(r.data, '$.city') = ?
         )
    """

    def __init__(self, model: Type[SQLerModel], path: Sequence[Union[str, int]]):
        self.model = model
        self.path: List[Union[str, int]] = list(path)

    def _build_exists(self, op: str, val: Any) -> SQLerExpression:
        if not self.path:
            raise ValueError("Empty path for model field")
        first = self.path[0]
        if not isinstance(first, str):
            raise ValueError("First path segment must be a relation field name")
        # related table name is default-plural of field type's class; we rely on registry-set table on model
        # find table by inspecting registry mapping done in set_db; use child model's _table
        # fall back to pluralized field name if unknown
        try:
            # try to resolve via model field annotation
            rel_model = self.model.model_fields[first].annotation  # type: ignore[attr-defined]
            table = getattr(rel_model, "_table", None) or getattr(rel_model, "__name__", "")
            if not table or not isinstance(table, str):
                table = f"{first.lower()}s"
        except Exception:
            table = f"{first.lower()}s"

        rest = self.path[1:]
        json_rest = "".join(
            (f"[{p}]" if isinstance(p, int) else f".{p}") for p in rest
        )
        ref_json = f"$.{first}._id"
        # reference outer table explicitly to avoid inner column shadowing
        outer_table = getattr(self.model, "_table", None) or self.model.__name__.lower() + "s"
        where_right = f"json_extract(r.data, '${json_rest}') {op} ?" if rest else f"r._id {op} ?"
        sql = (
            "EXISTS (SELECT 1 FROM "
            f"{table} r WHERE r._id = json_extract({outer_table}.data, '{ref_json}') AND {where_right})"
        )
        return SQLerExpression(sql, [val])

    def __compare(self, op: str, val: Any) -> SQLerExpression:
        return self._build_exists(op, val)

    def __eq__(self, other: Any) -> SQLerExpression:  # type: ignore[override]
        return self.__compare("=", other)

    def __ne__(self, other: Any) -> SQLerExpression:  # type: ignore[override]
        return self.__compare("!=", other)

    def __gt__(self, other: Any) -> SQLerExpression:
        return self.__compare(">", other)

    def __ge__(self, other: Any) -> SQLerExpression:
        return self.__compare(">=", other)

    def __lt__(self, other: Any) -> SQLerExpression:
        return self.__compare("<", other)

    def __le__(self, other: Any) -> SQLerExpression:
        return self.__compare("<=", other)
