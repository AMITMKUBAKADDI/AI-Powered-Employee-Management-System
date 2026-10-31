-- database/seed.sql
-- Seed 12 sample employee records for testing and AI queries

INSERT INTO employees (employee_name, manager_name, city, date_of_joining, is_active)
VALUES
    ('Rahul Sharma', 'Priya Nair', 'Bangalore', '2023-03-15', TRUE),
    ('Priya Nair', 'Vikram Malhotra', 'Bangalore', '2021-06-01', TRUE),
    ('Vikram Malhotra', NULL, 'Mumbai', '2019-01-10', TRUE),
    ('Ananya Iyer', 'Priya Nair', 'Bangalore', '2024-02-20', TRUE),
    ('Amit Verma', 'Priya Nair', 'Mysore', '2025-02-01', TRUE),
    ('Sneha Patel', 'Vikram Malhotra', 'Mumbai', '2022-11-12', TRUE),
    ('Rohan Kulkarni', 'Sneha Patel', 'Pune', '2025-03-10', TRUE),
    ('Deepak Rao', 'Rahul Sharma', 'Bangalore', '2023-08-01', FALSE),
    ('Kavita Singh', 'Sneha Patel', 'Delhi', '2024-10-05', TRUE),
    ('Arjun Reddy', 'Vikram Malhotra', 'Hyderabad', '2025-01-15', TRUE),
    ('Meera Joshi', 'Arjun Reddy', 'Hyderabad', '2024-05-18', FALSE),
    ('Rahul Sharma', 'Sneha Patel', 'Delhi', '2025-04-01', TRUE) -- duplicate name to test disambiguation by ID
ON CONFLICT DO NOTHING;
