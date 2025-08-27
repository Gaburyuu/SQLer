from __future__ import annotations

from typing import Dict, Optional, Type


_REGISTRY: Dict[str, type] = {}


def register(table: str, cls: type) -> None:
    _REGISTRY[table] = cls


def resolve(table: str) -> Optional[type]:
    return _REGISTRY.get(table)

