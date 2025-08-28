import sqlite3
import threading
from typing import Any, Optional, Self

from .abstract import AdapterABC, NotConnectedError


class SQLiteAdapter(AdapterABC):
    """Synchronous SQLite connector w/ built in pragmas"""

    def __init__(self, path: str = "sqler.db", pragmas: Optional[list[str]] = None):
        """pragmas are an optional list of sql statements to apply on connection"""

        self.path = path
        self.connection: Optional[sqlite3.Connection] = None
        self.pragmas = pragmas
        self._lock = threading.RLock()

    def connect(self) -> None:
        self.connection = sqlite3.connect(
            self.path,
            uri=True,
            check_same_thread=False,
        )
        # row access by name + safe concurrent reads of row columns
        self.connection.row_factory = sqlite3.Row

        cursor = self.connection.cursor()

        pragmas = self.pragmas or []

        for pragma in pragmas:
            cursor.execute(pragma)
        self.connection.commit()

    def close(self) -> None:
        if self.connection:
            with self._lock:
                self.connection.close()
                self.connection = None

    def execute(self, query: str, params: Optional[list[Any]] = None) -> sqlite3.Cursor:
        """Execute a SQL query with optional parameters and return cursor"""
        if not self.connection:
            raise NotConnectedError("Database not connected, call connect() first")
        with self._lock:
            cursor = self.connection.cursor()
            if params is not None:
                # normalize list → tuple to please sqlite API and avoid surprises
                if isinstance(params, list):
                    params = tuple(params)
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            return _LockedCursor(cursor, self._lock)

    def executemany(self, query: str, param_list: Optional[list[Any]]) -> sqlite3.Cursor:
        """Execute a param query multiple times with different parameter sets"""
        if not self.connection:
            raise NotConnectedError("Database not connected, call connect() first")
        with self._lock:
            cursor = self.connection.cursor()
            cursor.executemany(query, param_list or [])
            self.connection.commit()
            return _LockedCursor(cursor, self._lock)

    def executescript(self, script: str) -> sqlite3.Cursor:
        """Execute multiple statements from a script in a single action"""
        if not self.connection:
            raise NotConnectedError("Database not connected, call connect() first")
        with self._lock:
            cursor = self.connection.cursor()
            cursor.executescript(script)
            self.connection.commit()
            return _LockedCursor(cursor, self._lock)

    def commit(self) -> None:
        """Commit the current transaction."""
        if not self.connection:
            raise NotConnectedError("Database not connected, call connect() first")
        with self._lock:
            self.connection.commit()

    def __enter__(self):
        """Enter context manager; connect if not connected"""
        if not self.connection:
            self.connect()
        return self

    def __exit__(self, exception_type, exception_value, exception_tracebak):
        """Exit context manager; commit or rollback depending on exceptions"""
        if not self.connection:
            return
        with self._lock:
            if exception_type is None:
                self.connection.commit()
            else:
                self.connection.rollback()

    ### factories

    @classmethod
    def in_memory(cls, shared: bool = True) -> Self:
        """Connects to an in memory db with some pragmas applied"""
        pragmas = [
            "PRAGMA foreign_keys = ON",
            "PRAGMA synchronous = OFF",
            "PRAGMA journal_mode = MEMORY",
            "PRAGMA temp_store = MEMORY",
            "PRAGMA cache_size = -32000",
            "PRAGMA locking_mode = EXCLUSIVE",
        ]
        if shared:
            uri = "file::memory:?cache=shared"
        else:
            uri = ":memory:"
        return cls(uri, pragmas=pragmas)

    @classmethod
    def on_disk(cls, path: str = "sqler.db") -> Self:
        """Connects (creates if not exist) a db on disk with some pragmas applied"""
        pragmas = [
            "PRAGMA foreign_keys = ON",
            "PRAGMA busy_timeout = 5000",
            "PRAGMA journal_mode = WAL",
            "PRAGMA synchronous = NORMAL",
            "PRAGMA cache_size = -64000",
            "PRAGMA wal_autocheckpoint = 1000",
            "PRAGMA mmap_size = 268435456",
            "PRAGMA temp_store = MEMORY",
        ]
        return cls(path, pragmas=pragmas)


class _LockedCursor:
    """Thread-safe wrapper around sqlite3.Cursor that acquires the adapter lock
    for fetch and attribute access that reads cursor state.
    """

    def __init__(self, cursor: sqlite3.Cursor, lock: threading.RLock):
        self._cursor = cursor
        self._lock = lock

    def fetchone(self):
        with self._lock:
            return self._cursor.fetchone()

    def fetchall(self):
        with self._lock:
            return self._cursor.fetchall()

    def fetchmany(self, size: int | None = None):
        with self._lock:
            if size is None:
                return self._cursor.fetchmany()
            return self._cursor.fetchmany(size)

    @property
    def rowcount(self):
        with self._lock:
            return self._cursor.rowcount

    @property
    def lastrowid(self):
        with self._lock:
            return self._cursor.lastrowid

    def __iter__(self):
        # Iteration under lock would serialize the whole generator; fetchall instead in code
        with self._lock:
            return iter(self._cursor.fetchall())

    def __getattr__(self, name: str):
        # Fallback for any other cursor attributes
        return getattr(self._cursor, name)
