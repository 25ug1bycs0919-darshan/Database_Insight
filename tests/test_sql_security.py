import sqlite3

import pytest

from insightsql.sql_security import (
    SQLValidationError,
    make_read_only_authorizer,
    validate_select,
)


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT * FROM Employees",
        "  select employee_id FROM employees",
        "-- report query\nSELECT COUNT(*) FROM Projects",
        "/* read only */ SELECT name FROM Departments",
    ],
)
def test_accepts_select(sql):
    assert validate_select(sql) == sql


@pytest.mark.parametrize(
    "sql",
    [
        "",
        "DROP TABLE Employees",
        "DELETE FROM Employees",
        "UPDATE Employees SET salary = 0",
        "ALTER TABLE Employees ADD COLUMN x",
        "TRUNCATE TABLE Employees",
        "INSERT INTO Employees VALUES (1)",
        "WITH staff AS (SELECT * FROM Employees) SELECT * FROM staff",
        "/* unclosed comment SELECT * FROM Employees",
    ],
)
def test_rejects_non_select_statements(sql):
    with pytest.raises(SQLValidationError):
        validate_select(sql)


def test_sqlite_rejects_multiple_statements():
    connection = sqlite3.connect(":memory:")
    connection.set_authorizer(make_read_only_authorizer())
    with pytest.raises(sqlite3.ProgrammingError):
        connection.execute("SELECT 1; SELECT 2")
    connection.close()


def test_sqlite_authorizer_rejects_non_allowlisted_table():
    connection = sqlite3.connect(":memory:")
    connection.set_authorizer(make_read_only_authorizer())
    with pytest.raises(sqlite3.DatabaseError):
        connection.execute("SELECT name FROM sqlite_schema")
    connection.close()
