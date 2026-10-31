-- database/schema.sql
-- Schema definition for AI-Powered Employee Management System

-- Drop existing table and functions if needed (clean setup)
-- DROP TABLE IF EXISTS employees CASCADE;

CREATE TABLE IF NOT EXISTS employees (
    employee_id SERIAL PRIMARY KEY,
    employee_name VARCHAR(150) NOT NULL,
    manager_name VARCHAR(150),
    city VARCHAR(100),
    date_of_joining DATE NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_on TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    modified_on TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Trigger function to automatically update modified_on timestamp
CREATE OR REPLACE FUNCTION update_employee_modified_on()
RETURNS TRIGGER AS $$
BEGIN
    NEW.modified_on = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_employees_modified_on ON employees;

CREATE TRIGGER trg_employees_modified_on
BEFORE UPDATE ON employees
FOR EACH ROW
EXECUTE FUNCTION update_employee_modified_on();

-- Performance Indexes aligned with query patterns
CREATE INDEX IF NOT EXISTS idx_employees_name_lower ON employees (LOWER(employee_name));
CREATE INDEX IF NOT EXISTS idx_employees_city_lower ON employees (LOWER(city));
CREATE INDEX IF NOT EXISTS idx_employees_is_active ON employees (is_active);
CREATE INDEX IF NOT EXISTS idx_employees_date_of_joining ON employees (date_of_joining);
CREATE INDEX IF NOT EXISTS idx_employees_manager_name_lower ON employees (LOWER(manager_name));
