-- Schema, indexes, and integrity triggers for the employee management database.
PRAGMA foreign_keys = ON;

BEGIN IMMEDIATE;

CREATE TABLE Departments (
    department_id INTEGER PRIMARY KEY,
    department_name TEXT NOT NULL COLLATE NOCASE UNIQUE
        CHECK (length(trim(department_name)) > 0),
    location TEXT NOT NULL
        CHECK (length(trim(location)) > 0)
);

CREATE TABLE Employees (
    employee_id INTEGER PRIMARY KEY,
    first_name TEXT NOT NULL CHECK (length(trim(first_name)) > 0),
    last_name TEXT NOT NULL CHECK (length(trim(last_name)) > 0),
    email TEXT NOT NULL COLLATE NOCASE UNIQUE
        CHECK (email = trim(email) AND instr(email, '@') > 1),
    job_title TEXT NOT NULL CHECK (length(trim(job_title)) > 0),
    hire_date TEXT NOT NULL
        CHECK (
            hire_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'
            AND date(hire_date, '+0 days') = hire_date
        ),
    salary NUMERIC NOT NULL CHECK (salary >= 0),
    department_id INTEGER NOT NULL,
    FOREIGN KEY (department_id)
        REFERENCES Departments (department_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);

CREATE TABLE Projects (
    project_id INTEGER PRIMARY KEY,
    project_name TEXT NOT NULL UNIQUE
        CHECK (length(trim(project_name)) > 0),
    description TEXT,
    start_date TEXT NOT NULL
        CHECK (
            start_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'
            AND date(start_date, '+0 days') = start_date
        ),
    end_date TEXT
        CHECK (
            end_date IS NULL OR (
                end_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'
                AND date(end_date, '+0 days') = end_date
                AND end_date >= start_date
            )
        ),
    status TEXT NOT NULL
        CHECK (status IN ('Planned', 'Active', 'Completed', 'On Hold')),
    department_id INTEGER NOT NULL,
    FOREIGN KEY (department_id)
        REFERENCES Departments (department_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);

CREATE TABLE Employee_Projects (
    employee_id INTEGER NOT NULL,
    project_id INTEGER NOT NULL,
    project_role TEXT NOT NULL CHECK (length(trim(project_role)) > 0),
    assigned_on TEXT NOT NULL
        CHECK (
            assigned_on GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'
            AND date(assigned_on, '+0 days') = assigned_on
        ),
    allocation_percent INTEGER NOT NULL
        CHECK (allocation_percent BETWEEN 1 AND 100),
    PRIMARY KEY (employee_id, project_id),
    FOREIGN KEY (employee_id)
        REFERENCES Employees (employee_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    FOREIGN KEY (project_id)
        REFERENCES Projects (project_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE
);

CREATE INDEX idx_employees_department_id ON Employees (department_id);
CREATE INDEX idx_projects_department_id ON Projects (department_id);
CREATE INDEX idx_employee_projects_project_id ON Employee_Projects (project_id);

CREATE TRIGGER employee_projects_allocation_insert
BEFORE INSERT ON Employee_Projects
WHEN COALESCE(
    (SELECT SUM(allocation_percent)
     FROM Employee_Projects
     WHERE employee_id = NEW.employee_id),
    0
) + NEW.allocation_percent > 100
BEGIN
    SELECT RAISE(ABORT, 'employee allocation cannot exceed 100 percent');
END;

CREATE TRIGGER employee_projects_allocation_update
BEFORE UPDATE OF employee_id, allocation_percent ON Employee_Projects
WHEN COALESCE(
    (SELECT SUM(allocation_percent)
     FROM Employee_Projects
     WHERE employee_id = NEW.employee_id
       AND NOT (
           employee_id = OLD.employee_id
           AND project_id = OLD.project_id
       )),
    0
) + NEW.allocation_percent > 100
BEGIN
    SELECT RAISE(ABORT, 'employee allocation cannot exceed 100 percent');
END;

CREATE TRIGGER employee_projects_dates_insert
BEFORE INSERT ON Employee_Projects
WHEN NOT EXISTS (
    SELECT 1
    FROM Projects
    WHERE project_id = NEW.project_id
      AND NEW.assigned_on >= start_date
      AND (end_date IS NULL OR NEW.assigned_on <= end_date)
)
BEGIN
    SELECT RAISE(ABORT, 'assignment date must fall within the project dates');
END;

CREATE TRIGGER employee_projects_dates_update
BEFORE UPDATE OF project_id, assigned_on ON Employee_Projects
WHEN NOT EXISTS (
    SELECT 1
    FROM Projects
    WHERE project_id = NEW.project_id
      AND NEW.assigned_on >= start_date
      AND (end_date IS NULL OR NEW.assigned_on <= end_date)
)
BEGIN
    SELECT RAISE(ABORT, 'assignment date must fall within the project dates');
END;

CREATE TRIGGER projects_dates_update
BEFORE UPDATE OF start_date, end_date ON Projects
WHEN EXISTS (
    SELECT 1
    FROM Employee_Projects
    WHERE project_id = OLD.project_id
      AND (
          assigned_on < NEW.start_date
          OR (NEW.end_date IS NOT NULL AND assigned_on > NEW.end_date)
      )
)
BEGIN
    SELECT RAISE(ABORT, 'project dates cannot exclude existing assignments');
END;

COMMIT;
