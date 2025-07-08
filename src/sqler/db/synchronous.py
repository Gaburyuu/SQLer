import sqlite3
from typing import Optional, Any
from .abstract import DBABC, NotConnectedError


class SQLiteDB(DBABC):
    """Synchronous SQLite connector w/ built in pragmas"""

    def __init__(self, path: str = "sqler.db", pragmas: Optional[list[str]] = None):
        """pragmas are an optional list of sql statements to apply on connection"""

        self.path = path
        self.connection: Optional[sqlite3.Connection] = None
        self.pragmas = pragmas

    def connect(self) -> None:
        self.connection = sqlite3.connect(
            self.path,
            uri=True,
            check_same_thread=False,
        )

        cursor = self.connection.cursor()

        pragmas = self.pragmas or []

        for pragma in pragmas:
            cursor.execute(pragma)
        self.connection.commit()

    def close(self) -> None:
        if self.connection:
            self.connection.close()
            self.connection = None

    def execute(self, query: str, params: Optional[list[Any]] = None) -> sqlite3.Cursor:
        """Execute a SQL query with optional parameters and return cursor"""
        if not self.connection:
            raise NotConnectedError("Database not connected, call connect() first")
        cursor = self.connection.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        return cursor

    def executemany(
        self, query: str, param_list: Optional[list[Any]]
    ) -> sqlite3.Cursor:
        """Execute a param query multiple times with different parameter sets"""
        if not self.connection:
            raise NotConnectedError("Database not connected, call connect() first")
        cursor = self.connection.cursor()
        cursor.executemany(query, param_list)
        self.commit()
        return cursor

    def executescript(self, script: str) -> sqlite3.Cursor:
        """Execute multiple statements from a script in a single action"""
        if not self.connection:
            raise NotConnectedError("Database not connected, call connect() first")
        cursor = self.connection.cursor()
        cursor.executescript(script)
        self.connection.commit()
        return cursor

    def commit(self) -> None:
        """Commit the current transaction."""
        if not self.connection:
            raise NotConnectedError("Database not connected, call connect() first")
        self.connection.commit()

    def __enter__(self):
        """Enter context manager; connect if not connected"""
        if not self.connection:
            self.connect()
        return self

    def __exit__(self, exception_type, exception_value, exception_tracebak):
        """Exit context manager; commit or rollback depending on exceptions"""
        if exception_type is None:
            self.connection.commit()
        else:
            self.connection.rollback()

    ### factories

    @classmethod
    def in_memory(cls, shared: bool = True) -> "SQLiteDB":
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
    def from_file(cls, path: str = "sqler.db") -> "SQLiteDB":
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
