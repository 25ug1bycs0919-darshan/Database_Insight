import sqlite3
from pathlib import Path

import pytest

from insightsql.database import (
    MAX_RESULT_ROWS,
    DatabaseError,
    execute_select,
)
from insightsql.sql_security import SQLValidationError


def make_test_database(path: Path) -> None:
    connection = sqlite3.connect(path)
    connection.execute("CREATE TABLE Employees (employee_id INTEGER, first_name TEXT)")
    connection.executemany(
        "INSERT INTO Employees VALUES (?, ?)",
        [(index, f"Employee {index}") for index in range(MAX_RESULT_ROWS + 5)],
    )
    connection.commit()
    connection.close()


def test_executes_select_from_read_only_database(tmp_path):
    database_path = tmp_path / "test.db"
    make_test_database(database_path)

    result = execute_select(database_path, "SELECT employee_id FROM Employees LIMIT 2")

    assert result.columns == ["employee_id"]
    assert result.rows == [(0,), (1,)]
    assert not result.truncated


def test_caps_results_and_marks_them_truncated(tmp_path):
    database_path = tmp_path / "test.db"
    make_test_database(database_path)

    result = execute_select(database_path, "SELECT * FROM Employees")

    assert len(result.rows) == MAX_RESULT_ROWS
    assert result.truncated


@pytest.mark.parametrize(
    "sql",
    [
        "DELETE FROM Employees",
        "UPDATE Employees SET first_name = 'Changed'",
        "INSERT INTO Employees VALUES (999, 'Changed')",
        "DROP TABLE Employees",
        "PRAGMA table_info(Employees)",
        "SELECT name FROM sqlite_schema",
        "SELECT load_extension('extension')",
        "SELECT randomblob(100)",
    ],
)
def test_rejects_unsafe_queries(tmp_path, sql):
    database_path = tmp_path / "test.db"
    make_test_database(database_path)

    with pytest.raises((SQLValidationError, DatabaseError)):
        execute_select(database_path, sql)

    connection = sqlite3.connect(database_path)
    assert connection.execute("SELECT COUNT(*) FROM Employees").fetchone()[0] == (
        MAX_RESULT_ROWS + 5
    )
    connection.close()


def test_missing_database_has_friendly_error(tmp_path):
    with pytest.raises(DatabaseError, match="not found"):
        execute_select(tmp_path / "missing.db", "SELECT 1")
