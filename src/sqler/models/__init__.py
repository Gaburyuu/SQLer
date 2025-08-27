from .model import SQLerModel
from .queryset import SQLerQuerySet
from .safe import SQLerSafeModel, StaleVersionError
from .async_model import AsyncSQLerModel
from .async_queryset import AsyncSQLerQuerySet
from .async_safe import AsyncSQLerSafeModel
from .model_field import SQLerModelField
from .ref import SQLerRef, as_ref
from dataclasses import dataclass


class ReferentialIntegrityError(RuntimeError):
    """Raised when delete(on_delete='restrict') hits referencing rows."""


@dataclass
class BrokenRef:
    table: str
    row_id: int
    path: str
    target_table: str
    target_id: int

__all__ = [
    "SQLerModel",
    "SQLerQuerySet",
    "SQLerSafeModel",
    "StaleVersionError",
    "AsyncSQLerModel",
    "AsyncSQLerQuerySet",
    "AsyncSQLerSafeModel",
    "SQLerModelField",
    "SQLerRef",
    "as_ref",
    "ReferentialIntegrityError",
    "BrokenRef",
]
