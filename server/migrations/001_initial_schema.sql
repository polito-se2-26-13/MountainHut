-- ====================================================================
-- Migration: 001_initial_schema.sql
-- Description: Initial MountainHut database schema based on context.md and stories.md
-- ====================================================================

PRAGMA foreign_keys = ON;

-- --------------------------------------------------------------------
-- Schema Migrations Tracking
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(100) PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- --------------------------------------------------------------------
-- 1. Hut Profile & Information (context.md)
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS hut_info (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(150) NOT NULL,
    description TEXT,
    location VARCHAR(255),
    altitude_m INTEGER,
    how_to_reach TEXT,
    points_of_interest TEXT,
    contact_email VARCHAR(255),
    contact_phone VARCHAR(50),
    has_ebike_charging BOOLEAN NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- --------------------------------------------------------------------
-- 2. Users: Hikers, Employees, Wardens / Managers (context.md)
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
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
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_user_role CHECK (role IN ('Hiker', 'Employee', 'Warden', 'Manager'))
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);

-- --------------------------------------------------------------------
-- 3. Hut Tables (MH-01 & MH-02)
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tables (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    table_number VARCHAR(50) NOT NULL UNIQUE,
    capacity INTEGER NOT NULL CHECK (capacity > 0),
    location VARCHAR(100),
    is_active BOOLEAN NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_tables_table_number ON tables(table_number);

-- --------------------------------------------------------------------
-- 4. Meal Time Slots (MH-01 & MH-02)
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS time_slots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    meal_type VARCHAR(50),
    status VARCHAR(20) NOT NULL DEFAULT 'OPEN',
    notes VARCHAR(255),
    created_by_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_slots_creator FOREIGN KEY (created_by_id) REFERENCES users(id) ON DELETE SET NULL,
    CONSTRAINT chk_slot_status CHECK (status IN ('OPEN', 'CLOSED', 'CANCELLED'))
);

CREATE INDEX IF NOT EXISTS idx_time_slots_date ON time_slots(date);
CREATE INDEX IF NOT EXISTS idx_time_slots_status ON time_slots(status);

-- --------------------------------------------------------------------
-- 5. Slot Table Capacity (MH-02: define set of tables & seats per slot)
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS slot_tables (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slot_id INTEGER NOT NULL,
    table_id INTEGER NOT NULL,
    available_seats INTEGER NOT NULL CHECK (available_seats >= 0),
    is_available BOOLEAN NOT NULL DEFAULT 1,
    CONSTRAINT fk_slot_tables_slot FOREIGN KEY (slot_id) REFERENCES time_slots(id) ON DELETE CASCADE,
    CONSTRAINT fk_slot_tables_table FOREIGN KEY (table_id) REFERENCES tables(id) ON DELETE CASCADE,
    CONSTRAINT uq_slot_table UNIQUE (slot_id, table_id)
);

CREATE INDEX IF NOT EXISTS idx_slot_tables_slot_id ON slot_tables(slot_id);
CREATE INDEX IF NOT EXISTS idx_slot_tables_table_id ON slot_tables(table_id);

-- --------------------------------------------------------------------
-- 6. Reservations (MH-01 & MH-03)
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS reservations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    booking_reference VARCHAR(32) NOT NULL UNIQUE,
    user_id INTEGER NOT NULL,
    slot_id INTEGER NOT NULL,
    party_size INTEGER NOT NULL CHECK (party_size > 0),
    special_requirements TEXT,
    contact_name VARCHAR(200) NOT NULL,
    contact_email VARCHAR(255) NOT NULL,
    contact_phone VARCHAR(50),
    status VARCHAR(20) NOT NULL DEFAULT 'CONFIRMED',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_res_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_res_slot FOREIGN KEY (slot_id) REFERENCES time_slots(id) ON DELETE CASCADE,
    CONSTRAINT uq_user_slot_reservation UNIQUE (user_id, slot_id),
    CONSTRAINT chk_res_status CHECK (status IN ('CONFIRMED', 'CANCELLED', 'COMPLETED', 'NO_SHOW'))
);

CREATE INDEX IF NOT EXISTS idx_reservations_booking_ref ON reservations(booking_reference);
CREATE INDEX IF NOT EXISTS idx_reservations_user_id ON reservations(user_id);
CREATE INDEX IF NOT EXISTS idx_reservations_slot_id ON reservations(slot_id);

-- --------------------------------------------------------------------
-- 7. Reservation Table Assignments (MH-01: Table sharing & splitting)
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS reservation_table_assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reservation_id INTEGER NOT NULL,
    slot_table_id INTEGER NOT NULL,
    assigned_seats INTEGER NOT NULL CHECK (assigned_seats > 0),
    CONSTRAINT fk_rta_reservation FOREIGN KEY (reservation_id) REFERENCES reservations(id) ON DELETE CASCADE,
    CONSTRAINT fk_rta_slot_table FOREIGN KEY (slot_table_id) REFERENCES slot_tables(id) ON DELETE CASCADE,
    CONSTRAINT uq_reservation_slot_table UNIQUE (reservation_id, slot_table_id)
);

CREATE INDEX IF NOT EXISTS idx_rta_reservation_id ON reservation_table_assignments(reservation_id);
CREATE INDEX IF NOT EXISTS idx_rta_slot_table_id ON reservation_table_assignments(slot_table_id);

