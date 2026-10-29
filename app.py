"""Streamlit entry point for InsightSQL."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st

from insightsql.database import (
    MAX_RESULT_ROWS,
    DatabaseError,
    execute_select,
)
from insightsql.llm import (
    AgentConfigurationError,
    AgentError,
    generate_sql,
)
from insightsql.sql_security import SQLValidationError, validate_select

APP_DIR = Path(__file__).resolve().parent
DATABASE_PATH = Path(
    os.getenv("INSIGHTSQL_DATABASE", str(APP_DIR / "employee_management.db"))
)
MAX_HISTORY_ITEMS = 100
APP_BUILD = "2026-10-29.4"

logging.basicConfig(
    level=os.getenv("INSIGHTSQL_LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("insightsql.ui")

SCHEMA_CONTEXT = """
Departments(department_id, department_name, location)
Employees(employee_id, first_name, last_name, email, job_title, hire_date,
          salary, department_id)
Projects(project_id, project_name, description, start_date, end_date, status,
         department_id)
Employee_Projects(employee_id, project_id, project_role, assigned_on,
                  allocation_percent)

Relationships:
- Employees.department_id references Departments.department_id.
- Projects.department_id references Departments.department_id.
- Employee_Projects.employee_id references Employees.employee_id.
- Employee_Projects.project_id references Projects.project_id.

Generate one SQLite SELECT statement only. Do not generate writes, PRAGMA,
ATTACH, comments, or markdown fences. Use only these four tables.
"""

st.set_page_config(page_title="InsightSQL", page_icon="🔎", layout="wide")


def _append_history(entry: dict[str, object]) -> None:
    history = st.session_state.setdefault("query_history", [])
    history.insert(0, entry)
    del history[MAX_HISTORY_ITEMS:]


def _render_history() -> None:
    history = st.session_state.get("query_history", [])
    st.subheader("Query history")
    if not history:
        st.caption("Queries you run will appear here for this session.")
        return

    for entry in history:
        question = str(entry["question"])
        status = str(entry["status"])
        label = f"{status} · {question[:90]}"
        with st.expander(label, expanded=False):
            st.caption(str(entry["created_at"]))
            st.code(str(entry["sql"]), language="sql")
            if status == "Success":
                st.caption(f"{entry['row_count']} row(s) returned")
            else:
                st.error(str(entry["message"]))


def _generate(question: str, api_key: str) -> None:
    try:
        sql = generate_sql(question, SCHEMA_CONTEXT, api_key=api_key)
        validate_select(sql)
    except AgentConfigurationError as error:
        st.error(str(error))
        return
    except AgentError as error:
        request_id = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        logger.error("SQL generation failed request_id=%s error=%s", request_id, error)
        st.error(f"{error} Reference: {request_id}")
        return
    except SQLValidationError as error:
        logger.warning("Generated SQL rejected: %s", error)
        st.error(f"The generated query was rejected: {error}")
        return

    st.session_state["generated_sql"] = sql
    st.session_state["generated_question"] = question
    st.session_state.pop("sql_editor", None)
    st.session_state.pop("latest_result", None)


def _execute(question: str, sql: str) -> None:
    st.session_state.pop("latest_result", None)
    try:
        validate_select(sql)
        result = execute_select(DATABASE_PATH, sql)
    except SQLValidationError as error:
        st.error(f"Query rejected: {error}")
        return
    except DatabaseError as error:
        request_id = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        logger.exception("Query execution failed request_id=%s", request_id)
        _append_history(
            {
                "question": question,
                "sql": sql,
                "status": "Failed",
                "message": str(error),
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        st.error(f"{error} Reference: {request_id}")
        return

    _append_history(
        {
            "question": question,
            "sql": sql,
            "status": "Success",
            "row_count": len(result.rows),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    st.session_state["latest_result"] = {
        "question": question,
        "sql": sql,
        "columns": result.columns,
        "rows": result.rows,
        "truncated": result.truncated,
    }


def main() -> None:
    st.title("InsightSQL")
    st.caption(
        "Ask questions about your SQLite data. Generated SQL is shown before "
        "execution; only read-only SELECT queries are allowed."
    )

    with st.sidebar:
        st.header("Database")
        st.code(str(DATABASE_PATH), language=None)
        st.caption(f"Maximum displayed rows: {MAX_RESULT_ROWS:,}")
        st.info("Database access is read-only. Query history lasts for this session.")
        session_api_key = st.text_input(
            "OpenAI API key",
            type="password",
            help=(
                "Optional if OPENAI_API_KEY is set in the app's environment. "
                "This field is used only for this Streamlit session."
            ),
        )
        configured_api_key = session_api_key or os.getenv("OPENAI_API_KEY", "")
        if configured_api_key.strip():
            st.success("OpenAI API key is configured for this session.")
        else:
            st.warning(
                "Enter an OpenAI API key above or set OPENAI_API_KEY in the "
                "terminal that starts this app."
            )
        st.caption("HTTP 400 diagnostics: enabled")
        st.caption(f"App build: {APP_BUILD}")

    with st.form("question_form"):
        question = st.text_area(
            "Question",
            placeholder=(
                "Examples:\n"
                "- List employees in the Engineering department.\n"
                "- Show each project and its assigned employees.\n"
                "- Which departments have the most employees?"
            ),
            max_chars=2_000,
            height=130,
        )
        generate_clicked = st.form_submit_button(
            "Generate SQL", type="primary", use_container_width=True
        )

    if generate_clicked:
        if not question.strip():
            st.warning("Enter a question first.")
        else:
            _generate(question.strip(), configured_api_key.strip())

    generated_sql = st.session_state.get("generated_sql")
    if generated_sql:
        st.subheader("Review generated SQL")
        st.caption("Inspect or edit the query before running it.")
        edited_sql = st.text_area(
            "SQL query",
            value=generated_sql,
            height=180,
            key="sql_editor",
            label_visibility="collapsed",
        ) or ""
        try:
            validate_select(edited_sql)
            st.success("Validation passed: one read-only SELECT statement.")
        except SQLValidationError as error:
            st.error(f"Validation failed: {error}")

        if st.button("Validate and run query", type="primary"):
            _execute(
                str(st.session_state.get("generated_question", "")),
                edited_sql,
            )

    result = st.session_state.get("latest_result")
    if result:
        st.subheader("Query results")
        st.caption(f"Question: {result['question']}")
        st.dataframe(
            {
                column: [row[index] for row in result["rows"]]
                for index, column in enumerate(result["columns"])
            },
            use_container_width=True,
            hide_index=True,
        )
        if result["truncated"]:
            st.warning(
                f"Results were limited to the first {MAX_RESULT_ROWS:,} rows."
            )
        with st.expander("Executed SQL", expanded=False):
            st.code(result["sql"], language="sql")

    st.divider()
    _render_history()


if __name__ == "__main__":
    main()
