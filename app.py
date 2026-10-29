"""Read-only command-line browser for the employee management SQLite database."""

import argparse
import sqlite3
import sys
from pathlib import Path

PAGE_SIZE = 20
WRITE_ACTIONS = {
    sqlite3.SQLITE_INSERT,
    sqlite3.SQLITE_UPDATE,
    sqlite3.SQLITE_DELETE,
    sqlite3.SQLITE_CREATE_INDEX,
    sqlite3.SQLITE_CREATE_TABLE,
    sqlite3.SQLITE_CREATE_TEMP_INDEX,
    sqlite3.SQLITE_CREATE_TEMP_TABLE,
    sqlite3.SQLITE_CREATE_TEMP_TRIGGER,
    sqlite3.SQLITE_CREATE_TEMP_VIEW,
    sqlite3.SQLITE_CREATE_TRIGGER,
    sqlite3.SQLITE_CREATE_VIEW,
    sqlite3.SQLITE_DROP_INDEX,
    sqlite3.SQLITE_DROP_TABLE,
    sqlite3.SQLITE_DROP_TEMP_INDEX,
    sqlite3.SQLITE_DROP_TEMP_TABLE,
    sqlite3.SQLITE_DROP_TEMP_TRIGGER,
    sqlite3.SQLITE_DROP_TEMP_VIEW,
    sqlite3.SQLITE_DROP_TRIGGER,
    sqlite3.SQLITE_DROP_VIEW,
    sqlite3.SQLITE_ALTER_TABLE,
    sqlite3.SQLITE_REINDEX,
    sqlite3.SQLITE_ANALYZE,
    sqlite3.SQLITE_ATTACH,
    sqlite3.SQLITE_DETACH,
    sqlite3.SQLITE_TRANSACTION,
    sqlite3.SQLITE_SAVEPOINT,
    sqlite3.SQLITE_PRAGMA,
}


def deny_database_changes(action, _arg1, _arg2, _database, _trigger):
    """Deny database-writing operations, even if a future app feature issues one."""
    if action in WRITE_ACTIONS:
        return sqlite3.SQLITE_DENY
    return sqlite3.SQLITE_OK


def open_read_only(database_path):
    path = database_path.expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Database file not found: {path}")

    connection = sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True)
    connection.execute("PRAGMA query_only = ON")
    connection.set_authorizer(deny_database_changes)
    return connection


def get_tables(connection):
    rows = connection.execute(
        "SELECT name FROM sqlite_schema "
        "WHERE type = 'table' AND name NOT LIKE 'sqlite_%' "
        "ORDER BY name"
    ).fetchall()
    return [row[0] for row in rows]


def quote_identifier(identifier):
    return '"' + identifier.replace('"', '""') + '"'


def display_tables(connection, tables):
    print("\nTables")
    for index, table in enumerate(tables, start=1):
        count = connection.execute(
            f"SELECT COUNT(*) FROM {quote_identifier(table)}"
        ).fetchone()[0]
        print(f"{index}. {table} ({count} rows)")


def display_table(connection, table):
    quoted_table = quote_identifier(table)
    row_count = connection.execute(
        f"SELECT COUNT(*) FROM {quoted_table}"
    ).fetchone()[0]
    if row_count == 0:
        print(f"\n{table} has no rows.")
        return

    offset = 0
    while offset < row_count:
        cursor = connection.execute(
            f"SELECT * FROM {quoted_table} LIMIT ? OFFSET ?",
            (PAGE_SIZE, offset),
        )
        columns = [description[0] for description in cursor.description]
        rows = cursor.fetchall()

        print(f"\n{table} — rows {offset + 1}-{offset + len(rows)} of {row_count}")
        print(" | ".join(columns))
        for row in rows:
            print(" | ".join("" if value is None else str(value) for value in row))

        offset += len(rows)
        if offset < row_count:
            choice = input("Press Enter for next page, or type q to stop: ").strip()
            if choice.lower() == "q":
                break


def run_app(database_path):
    connection = open_read_only(database_path)
    try:
        tables = get_tables(connection)
        if not tables:
            print("No user tables found in the database.")
            return

        print(f"Employee Management Database (read-only): {database_path.resolve()}")
        while True:
            display_tables(connection, tables)
            choice = input("\nEnter a table number to view it, or q to quit: ").strip()
            if choice.lower() == "q":
                break
            if not choice.isdigit() or not 1 <= int(choice) <= len(tables):
                print("Choose a listed table number or q.")
                continue
            display_table(connection, tables[int(choice) - 1])
    finally:
        connection.close()


def main():
    parser = argparse.ArgumentParser(
        description="Browse the employee management database without changing it."
    )
    parser.add_argument(
        "--database",
        type=Path,
        default=Path(__file__).with_name("employee_management.db"),
        help="SQLite database path (default: employee_management.db next to this app)",
    )
    args = parser.parse_args()

    try:
        run_app(args.database)
    except (OSError, sqlite3.Error) as error:
        print(f"Unable to open or read the database: {error}", file=sys.stderr)
        return 1
    except (EOFError, KeyboardInterrupt):
        print("\nExiting.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
