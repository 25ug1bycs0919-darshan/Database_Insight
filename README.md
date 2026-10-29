# Employee Management System Database

This example database tracks departments, employees, projects, and employee assignments. The schema and sample data use SQLite-compatible SQL.

## ER diagram

```mermaid
erDiagram
    DEPARTMENTS ||--o{ EMPLOYEES : employs
    DEPARTMENTS ||--o{ PROJECTS : owns
    EMPLOYEES ||--o{ EMPLOYEE_PROJECTS : assigned_to
    PROJECTS ||--o{ EMPLOYEE_PROJECTS : has

    DEPARTMENTS {
        INTEGER department_id PK
        TEXT department_name UK
        TEXT location
    }
    EMPLOYEES {
        INTEGER employee_id PK
        TEXT first_name
        TEXT last_name
        TEXT email UK
        TEXT job_title
        DATE hire_date
        DECIMAL salary
        INTEGER department_id FK
    }
    PROJECTS {
        INTEGER project_id PK
        TEXT project_name
        TEXT description
        DATE start_date
        DATE end_date
        TEXT status
        INTEGER department_id FK
    }
    EMPLOYEE_PROJECTS {
        INTEGER employee_id PK, FK
        INTEGER project_id PK, FK
        TEXT project_role
        DATE assigned_on
        INTEGER allocation_percent
    }
```

## Table definitions and keys

| Table | Purpose and columns | Keys |
|---|---|---|
| `Departments` | `department_id` (integer), `department_name` (text), `location` (text) | Primary key: `department_id`; unique: `department_name` |
| `Employees` | `employee_id` (integer), `first_name` (text), `last_name` (text), `email` (text), `job_title` (text), `hire_date` (date), `salary` (decimal), `department_id` (integer) | Primary key: `employee_id`; unique: `email`; foreign key: `department_id` → `Departments.department_id` |
| `Projects` | `project_id` (integer), `project_name` (text), `description` (text), `start_date` (date), `end_date` (date), `status` (text), `department_id` (integer) | Primary key: `project_id`; foreign key: `department_id` → `Departments.department_id` |
| `Employee_Projects` | `employee_id` (integer), `project_id` (integer), `project_role` (text), `assigned_on` (date), `allocation_percent` (integer, 1–100) | Composite primary key: (`employee_id`, `project_id`); foreign keys: `employee_id` → `Employees.employee_id`, `project_id` → `Projects.project_id` |

`Employees` and `Projects` have a many-to-many relationship represented by `Employee_Projects`. Each department can have multiple employees and projects. Deleting an employee or project removes its assignment rows; department deletion is restricted while employees or projects still reference it.

## Create and insert scripts

Run [`employee_management.sql`](./employee_management.sql) with SQLite to create all four tables and insert sample records. It includes **5 departments, 20 employees, 10 projects**, and example employee-project assignments. Foreign-key enforcement is enabled in the script.
