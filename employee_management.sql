PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS Departments (
    department_id INTEGER PRIMARY KEY,
    department_name TEXT NOT NULL UNIQUE,
    location TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS Employees (
    employee_id INTEGER PRIMARY KEY,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    job_title TEXT NOT NULL,
    hire_date TEXT NOT NULL,
    salary NUMERIC NOT NULL CHECK (salary >= 0),
    department_id INTEGER NOT NULL,
    FOREIGN KEY (department_id) REFERENCES Departments (department_id)
);

CREATE TABLE IF NOT EXISTS Projects (
    project_id INTEGER PRIMARY KEY,
    project_name TEXT NOT NULL,
    description TEXT,
    start_date TEXT NOT NULL,
    end_date TEXT,
    status TEXT NOT NULL CHECK (status IN ('Planned', 'Active', 'Completed', 'On Hold')),
    department_id INTEGER NOT NULL,
    CHECK (end_date IS NULL OR end_date >= start_date),
    FOREIGN KEY (department_id) REFERENCES Departments (department_id)
);

CREATE TABLE IF NOT EXISTS Employee_Projects (
    employee_id INTEGER NOT NULL,
    project_id INTEGER NOT NULL,
    project_role TEXT NOT NULL,
    assigned_on TEXT NOT NULL,
    allocation_percent INTEGER NOT NULL CHECK (allocation_percent BETWEEN 1 AND 100),
    PRIMARY KEY (employee_id, project_id),
    FOREIGN KEY (employee_id) REFERENCES Employees (employee_id) ON DELETE CASCADE,
    FOREIGN KEY (project_id) REFERENCES Projects (project_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_employees_department_id
    ON Employees (department_id);
CREATE INDEX IF NOT EXISTS idx_projects_department_id
    ON Projects (department_id);
CREATE INDEX IF NOT EXISTS idx_employee_projects_project_id
    ON Employee_Projects (project_id);

INSERT INTO Departments (department_id, department_name, location) VALUES
    (1, 'Engineering', 'Bengaluru'),
    (2, 'Human Resources', 'Bengaluru'),
    (3, 'Finance', 'Mumbai'),
    (4, 'Marketing', 'Delhi'),
    (5, 'Operations', 'Hyderabad');

INSERT INTO Employees (
    employee_id, first_name, last_name, email, job_title, hire_date, salary, department_id
) VALUES
    (1, 'Aarav', 'Sharma', 'aarav.sharma@example.com', 'Software Engineer', '2021-03-15', 85000, 1),
    (2, 'Ananya', 'Patel', 'ananya.patel@example.com', 'Senior Software Engineer', '2019-07-08', 112000, 1),
    (3, 'Rohan', 'Reddy', 'rohan.reddy@example.com', 'Database Administrator', '2020-11-02', 98000, 1),
    (4, 'Diya', 'Nair', 'diya.nair@example.com', 'QA Engineer', '2022-01-17', 78000, 1),
    (5, 'Ishaan', 'Gupta', 'ishaan.gupta@example.com', 'Engineering Manager', '2018-05-21', 135000, 1),
    (6, 'Meera', 'Iyer', 'meera.iyer@example.com', 'HR Manager', '2017-09-11', 105000, 2),
    (7, 'Kabir', 'Singh', 'kabir.singh@example.com', 'Recruiter', '2021-06-14', 68000, 2),
    (8, 'Sana', 'Khan', 'sana.khan@example.com', 'HR Generalist', '2023-02-06', 62000, 2),
    (9, 'Vikram', 'Joshi', 'vikram.joshi@example.com', 'Financial Analyst', '2020-04-20', 82000, 3),
    (10, 'Tara', 'Menon', 'tara.menon@example.com', 'Accountant', '2022-08-01', 70000, 3),
    (11, 'Arjun', 'Desai', 'arjun.desai@example.com', 'Finance Manager', '2016-12-05', 125000, 3),
    (12, 'Nisha', 'Rao', 'nisha.rao@example.com', 'Senior Accountant', '2019-10-28', 88000, 3),
    (13, 'Aditya', 'Kulkarni', 'aditya.kulkarni@example.com', 'Marketing Manager', '2018-02-12', 110000, 4),
    (14, 'Pooja', 'Shah', 'pooja.shah@example.com', 'Content Strategist', '2021-05-03', 74000, 4),
    (15, 'Neil', 'Fernandes', 'neil.fernandes@example.com', 'Digital Marketing Specialist', '2022-09-19', 72000, 4),
    (16, 'Kavya', 'Pillai', 'kavya.pillai@example.com', 'Brand Designer', '2020-06-08', 80000, 4),
    (17, 'Yash', 'Chopra', 'yash.chopra@example.com', 'Operations Manager', '2017-04-24', 115000, 5),
    (18, 'Ira', 'Bose', 'ira.bose@example.com', 'Business Analyst', '2020-12-14', 90000, 5),
    (19, 'Dev', 'Malhotra', 'dev.malhotra@example.com', 'Operations Coordinator', '2023-03-27', 64000, 5),
    (20, 'Riya', 'Das', 'riya.das@example.com', 'Process Improvement Lead', '2019-08-12', 97000, 5);

INSERT INTO Projects (
    project_id, project_name, description, start_date, end_date, status, department_id
) VALUES
    (1, 'Data Platform Modernization', 'Modernize the company data platform.', '2025-01-15', NULL, 'Active', 1),
    (2, 'Customer Portal', 'Build a self-service customer portal.', '2025-03-01', NULL, 'Active', 1),
    (3, 'Hiring Process Refresh', 'Improve recruiting workflows and tools.', '2025-02-10', NULL, 'Active', 2),
    (4, 'Employee Learning Program', 'Launch a company-wide learning program.', '2025-04-01', NULL, 'Planned', 2),
    (5, 'Annual Budget Review', 'Prepare and review the annual operating budget.', '2025-01-05', '2025-05-30', 'Completed', 3),
    (6, 'Expense Automation', 'Automate employee expense reporting.', '2025-06-01', NULL, 'Active', 3),
    (7, 'Brand Campaign 2025', 'Coordinate the annual brand campaign.', '2025-02-01', NULL, 'Active', 4),
    (8, 'Website Content Refresh', 'Refresh public website content and design.', '2025-05-15', NULL, 'Planned', 4),
    (9, 'Supply Chain Optimization', 'Improve supplier and inventory processes.', '2025-01-20', NULL, 'Active', 5),
    (10, 'Operations Dashboard', 'Create dashboards for operational metrics.', '2025-03-10', NULL, 'On Hold', 5);

INSERT INTO Employee_Projects (
    employee_id, project_id, project_role, assigned_on, allocation_percent
) VALUES
    (1, 1, 'Backend Engineer', '2025-01-15', 60),
    (2, 1, 'Technical Lead', '2025-01-15', 40),
    (3, 1, 'Database Administrator', '2025-01-20', 50),
    (4, 1, 'QA Engineer', '2025-02-01', 30),
    (5, 1, 'Project Sponsor', '2025-01-15', 10),
    (1, 2, 'Backend Engineer', '2025-03-01', 30),
    (2, 2, 'Technical Lead', '2025-03-01', 30),
    (4, 2, 'QA Engineer', '2025-03-05', 40),
    (6, 3, 'Project Sponsor', '2025-02-10', 10),
    (7, 3, 'Recruiter', '2025-02-10', 60),
    (8, 3, 'HR Generalist', '2025-02-12', 30),
    (6, 4, 'Program Lead', '2025-04-01', 20),
    (8, 4, 'Coordinator', '2025-04-01', 40),
    (9, 5, 'Financial Analyst', '2025-01-05', 50),
    (10, 5, 'Accountant', '2025-01-05', 50),
    (11, 5, 'Finance Lead', '2025-01-05', 20),
    (12, 6, 'Senior Accountant', '2025-06-01', 40),
    (9, 6, 'Business Analyst', '2025-06-01', 20),
    (13, 7, 'Campaign Lead', '2025-02-01', 40),
    (14, 7, 'Content Strategist', '2025-02-01', 50),
    (15, 7, 'Digital Marketing', '2025-02-03', 40),
    (16, 8, 'Brand Designer', '2025-05-15', 40),
    (14, 8, 'Content Strategist', '2025-05-15', 30),
    (17, 9, 'Operations Lead', '2025-01-20', 20),
    (18, 9, 'Business Analyst', '2025-01-20', 50),
    (19, 9, 'Operations Coordinator', '2025-01-22', 60),
    (20, 10, 'Process Improvement Lead', '2025-03-10', 30),
    (18, 10, 'Business Analyst', '2025-03-10', 20);
