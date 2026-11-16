-- ====================================================================
-- Migration: 004_special_requirements_schema.sql
-- Description: MH-05 Provide Party Requirements Schema & Seed Data
-- ====================================================================

PRAGMA foreign_keys = ON;

-- --------------------------------------------------------------------
-- 1. Table: special_requirements (MH-05)
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS special_requirements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reservation_id INTEGER NOT NULL,
    has_allergy BOOLEAN NOT NULL DEFAULT 0,
    description TEXT NOT NULL CHECK (length(trim(description)) > 0),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_special_req_reservation 
        FOREIGN KEY (reservation_id) REFERENCES reservations(id) ON DELETE CASCADE
);

-- Indexes for performance and kitchen allergy alert filtering
CREATE INDEX IF NOT EXISTS idx_spec_req_res_id 
    ON special_requirements(reservation_id);

CREATE INDEX IF NOT EXISTS idx_spec_req_allergy 
    ON special_requirements(has_allergy);

-- --------------------------------------------------------------------
-- 2. Seed Data from existing reservations
-- Res 1: '2 vegetarian meals, 1 gluten allergy' (1 allergy, 1 dietary)
-- Res 2: 'High chair requested for toddler' (0 allergy)
-- Res 3: 'Mountain hiking club group' (0 allergy)
-- --------------------------------------------------------------------
INSERT OR IGNORE INTO special_requirements (id, reservation_id, has_allergy, description) VALUES
(1, 1, 0, '2 vegetarian meals'),
(2, 1, 1, '1 gluten allergy'),
(3, 2, 0, 'High chair requested for toddler'),
(4, 3, 0, 'Mountain hiking club group');

