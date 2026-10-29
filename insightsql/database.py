"""Bounded, read-only SQLite query execution."""

from __future__ import annotations

import logging
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

from insightsql.sql_security import make_read_only_authorizer, validate_select

MAX_RESULT_ROWS = 500
MAX_QUERY_SECONDS = 5
PROGRESS_CHECK_INTERVAL = 1_000
logger = logging.getLogger(__name__)


class DatabaseError(RuntimeError):
    """Safe database operation failure intended for display to the user."""


@dataclass(frozen=True)
class QueryResult:
    columns: list[str]
    rows: list[tuple[object, ...]]
    truncated: bool


def _open_read_only(database_path: Path) -> sqlite3.Connection:
    path = database_path.expanduser().resolve()
    if not path.is_file():
        raise DatabaseError("The configured SQLite database file was not found.")

    connection: sqlite3.Connection | None = None
    try:
        connection = sqlite3.connect(
            f"{path.as_uri()}?mode=ro",
            uri=True,
            timeout=MAX_QUERY_SECONDS,
        )
        connection.execute("PRAGMA query_only = ON")
        connection.set_authorizer(make_read_only_authorizer())
        return connection
    except sqlite3.Error as error:
        if connection is not None:
            connection.close()
        raise DatabaseError("The SQLite database could not be opened.") from error


def execute_select(database_path: Path, sql: str) -> QueryResult:
    """Validate and execute a bounded SELECT using a read-only SQLite connection."""
    validate_select(sql)
    connection = _open_read_only(database_path)
    deadline = time.monotonic() + MAX_QUERY_SECONDS
    connection.set_progress_handler(
        lambda: int(time.monotonic() >= deadline),
        PROGRESS_CHECK_INTERVAL,
    )

    try:
        cursor = connection.execute(sql)
        if cursor.description is None:
            raise DatabaseError("The query did not return tabular results.")
        columns = [description[0] for description in cursor.description]
        rows = cursor.fetchmany(MAX_RESULT_ROWS + 1)
        truncated = len(rows) > MAX_RESULT_ROWS
        if truncated:
            rows = rows[:MAX_RESULT_ROWS]
        logger.info(
            "Read-only query completed row_count=%d truncated=%s",
            len(rows),
            truncated,
        )
        return QueryResult(columns=columns, rows=rows, truncated=truncated)
    except DatabaseError:
        raise
    except sqlite3.OperationalError as error:
        if "interrupted" in str(error).casefold():
            raise DatabaseError(
                f"The query exceeded the {MAX_QUERY_SECONDS}-second execution limit."
            ) from error
        logger.warning("SQLite rejected query: %s", error)
        raise DatabaseError(
            "SQLite could not run this query. Check the table and column names."
        ) from error
    except sqlite3.Error as error:
        logger.warning("SQLite query failed: %s", error)
        raise DatabaseError("The query could not be completed.") from error
    finally:
        connection.close()
