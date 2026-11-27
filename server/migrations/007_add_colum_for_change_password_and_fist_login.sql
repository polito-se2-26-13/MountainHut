PRAGMA foreign_keys = OFF;

BEGIN TRANSACTION;

-- 1. Create the new table
CREATE TABLE users_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    phone VARCHAR(50),
    role VARCHAR(50) NOT NULL DEFAULT 'Hiker',
    notes TEXT,
    emergency_contact VARCHAR(255),
    is_active BOOLEAN NOT NULL DEFAULT 1,
    must_change_password BOOLEAN NOT NULL DEFAULT 0,
    first_login BOOLEAN NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_user_role
        CHECK (role IN ('Hiker', 'Employee', 'Warden'))
);

-- 2. Copy existing data
INSERT INTO users_new (
    id,
    email,
    password_hash,
    first_name,
    last_name,
    phone,
    role,
    notes,
    emergency_contact,
    is_active,
    created_at,
    updated_at
)
SELECT
    id,
    email,
    password_hash,
    first_name,
    last_name,
    phone,
    role,
    notes,
    emergency_contact,
    is_active,
    created_at,
    updated_at
FROM users;

-- 3. Drop the old table
DROP TABLE users;

-- 4. Rename the new table
ALTER TABLE users_new RENAME TO users;

COMMIT;

PRAGMA foreign_keys = ON;