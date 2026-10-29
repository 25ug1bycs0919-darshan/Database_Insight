"""Validation helpers for the application's read-only SQL policy."""

from __future__ import annotations

import re
import sqlite3
from collections.abc import Callable

ALLOWED_TABLES = frozenset(
    {"departments", "employees", "projects", "employee_projects"}
)
ALLOWED_FUNCTIONS = frozenset(
    {
        "abs",
        "avg",
        "coalesce",
        "count",
        "date",
        "datetime",
        "dense_rank",
        "first_value",
        "group_concat",
        "ifnull",
        "instr",
        "julianday",
        "lag",
        "last_value",
        "lead",
        "length",
        "like",
        "lower",
        "ltrim",
        "max",
        "min",
        "nullif",
        "ntile",
        "rank",
        "replace",
        "round",
        "rtrim",
        "row_number",
        "strftime",
        "substr",
        "sum",
        "time",
        "total",
        "trim",
        "upper",
    }
)
MAX_SQL_LENGTH = 10_000
_SELECT_START = re.compile(r"SELECT\b", re.IGNORECASE)


class SQLValidationError(ValueError):
    """Raised when a query violates the read-only SQL policy."""


def _skip_leading_comments(sql: str) -> str:
    index = 0
    length = len(sql)
    while index < length:
        while index < length and sql[index].isspace():
            index += 1
        if sql.startswith("--", index):
            newline = sql.find("\n", index + 2)
            index = length if newline == -1 else newline + 1
            continue
        if sql.startswith("/*", index):
            end = sql.find("*/", index + 2)
            if end == -1:
                raise SQLValidationError("The SQL contains an unclosed comment.")
            index = end + 2
            continue
        break
    return sql[index:]


def validate_select(sql: str) -> str:
    """Require one non-empty SELECT statement and reject unsafe SQL shapes."""
    if not isinstance(sql, str) or not sql.strip():
        raise SQLValidationError("Enter a SQL query.")
    if len(sql) > MAX_SQL_LENGTH:
        raise SQLValidationError(
            f"SQL must be no longer than {MAX_SQL_LENGTH:,} characters."
        )

    statement = _skip_leading_comments(sql).lstrip()
    if not _SELECT_START.match(statement):
        raise SQLValidationError(
            "Only SELECT statements are allowed. CTEs and other statement types "
            "are not supported."
        )
    return sql


def make_read_only_authorizer() -> Callable[..., int]:
    """Return a SQLite authorizer that permits reads from approved tables only."""

    def authorize(
        action: int,
        arg1: str | None,
        arg2: str | None,
        _database: str | None,
        _trigger: str | None,
    ) -> int:
        if action == sqlite3.SQLITE_SELECT:
            return sqlite3.SQLITE_OK
        if action == sqlite3.SQLITE_READ:
            if arg1 and arg1.casefold() in ALLOWED_TABLES:
                return sqlite3.SQLITE_OK
            return sqlite3.SQLITE_DENY
        if action == sqlite3.SQLITE_FUNCTION:
            function_name = (arg2 or arg1 or "").casefold()
            return (
                sqlite3.SQLITE_OK
                if function_name in ALLOWED_FUNCTIONS
                else sqlite3.SQLITE_DENY
            )
        return sqlite3.SQLITE_DENY

    return authorize
