-- ====================================================================
-- Migration: 003_sprint2_availability_migration.sql
-- Description: TASK-05 & TASK-12 DB Migration & Sprint 2 Seed Test Data
-- Corresponds to MH-04: Check Availability, Indexing & Test Scenarios
-- ====================================================================

PRAGMA foreign_keys = ON;

-- --------------------------------------------------------------------
-- 1. TASK-12: Composite Performance Indexes for Real-Time Availability
-- --------------------------------------------------------------------

CREATE INDEX IF NOT EXISTS idx_slot_tables_slot_avail 
ON slot_tables(slot_id, is_available);

CREATE INDEX IF NOT EXISTS idx_reservations_slot_status 
ON reservations(slot_id, status);

CREATE INDEX IF NOT EXISTS idx_rta_slot_res 
ON reservation_table_assignments(slot_table_id, reservation_id);

CREATE INDEX IF NOT EXISTS idx_time_slots_date_status 
ON time_slots(date, status);

CREATE INDEX IF NOT EXISTS idx_time_slots_lookup 
ON time_slots(date, start_time, end_time);

-- --------------------------------------------------------------------
-- 2. TASK-05: Sprint 2 Test Data for Story MH-04 Availability Checks
-- --------------------------------------------------------------------

-- Tables for Sprint 2 scenarios (T7 .. T14)
INSERT OR IGNORE INTO tables (id, table_number, capacity, location, is_active) VALUES
(7,  'T7',  2, 'Terrace (Small Table)', 1),
(8,  'T8',  2, 'Terrace (Small Table)', 1),
(9,  'T9',  2, 'Terrace (Small Table)', 1),
(10, 'T10', 6, 'Main Dining Hall', 1),
(11, 'T11', 4, 'Main Dining Hall', 1),
(12, 'T12', 2, 'Stube Cozy Corner', 1),
(13, 'T13', 4, 'Indoor East', 1),
(14, 'T14', 4, 'Indoor West', 1);

-- --------------------------------------------------------------------
-- Time Slots for MH-04 Test Scenarios
-- --------------------------------------------------------------------

-- Slot 5: 3 tables of 2, all free (Total 6 seats).
-- Models MH-04 example: "with 6 free seats split over 3 tables of 2, a party of 6 is available"
INSERT OR IGNORE INTO time_slots (id, date, start_time, end_time, meal_type, status, notes, created_by_id) VALUES
(5, date('now', '+10 days'), '12:00:00', '13:00:00', 'Lunch', 'OPEN', 'Sprint 2 Scenario: 3 tables of 2', 2);

-- Slot 6: Free seats distributed as 2 + 3 + 1 (Total 6 free seats).
-- Models MH-04 example: "e.g. 2 + 3 + 1 seats"
INSERT OR IGNORE INTO time_slots (id, date, start_time, end_time, meal_type, status, notes, created_by_id) VALUES
(6, date('now', '+10 days'), '13:00:00', '14:00:00', 'Lunch', 'OPEN', 'Sprint 2 Scenario: 2 + 3 + 1 free layout', 2);

-- Slot 7: Fully booked slot (0 seats remaining)
INSERT OR IGNORE INTO time_slots (id, date, start_time, end_time, meal_type, status, notes, created_by_id) VALUES
(7, date('now', '+10 days'), '19:00:00', '20:30:00', 'Dinner', 'OPEN', 'Sprint 2 Scenario: Fully booked slot', 2);

-- Slot 8: Closed slot
INSERT OR IGNORE INTO time_slots (id, date, start_time, end_time, meal_type, status, notes, created_by_id) VALUES
(8, date('now', '+10 days'), '20:30:00', '22:00:00', 'Dinner', 'CLOSED', 'Sprint 2 Scenario: Closed slot', 2);

-- --------------------------------------------------------------------
-- Slot Tables Configuration
-- --------------------------------------------------------------------

-- Slot 5 Tables: T7 (2), T8 (2), T9 (2) -> total 6 seats
INSERT OR IGNORE INTO slot_tables (id, slot_id, table_id, available_seats, is_available) VALUES
(17, 5, 7, 2, 1),
(18, 5, 8, 2, 1),
(19, 5, 9, 2, 1);

-- Slot 6 Tables: T10 (6), T11 (4), T12 (2) -> total 12 seats
INSERT OR IGNORE INTO slot_tables (id, slot_id, table_id, available_seats, is_available) VALUES
(20, 6, 10, 6, 1),
(21, 6, 11, 4, 1),
(22, 6, 12, 2, 1);

-- Slot 7 Tables: T13 (4), T14 (4) -> total 8 seats
INSERT OR IGNORE INTO slot_tables (id, slot_id, table_id, available_seats, is_available) VALUES
(23, 7, 13, 4, 1),
(24, 7, 14, 4, 1);

-- Slot 8 Tables: T13 (4) -> total 4 seats (closed)
INSERT OR IGNORE INTO slot_tables (id, slot_id, table_id, available_seats, is_available) VALUES
(25, 8, 13, 4, 1);

-- --------------------------------------------------------------------
-- Confirmed Bookings for Slot 6 (Leaving 2 + 3 + 1 Free Seats)
-- --------------------------------------------------------------------

-- Res 4: party 4 on T10 (6 - 4 = 2 free seats left on T10)
INSERT OR IGNORE INTO reservations (
    id, booking_reference, user_id, slot_id, party_size, special_requirements,
    contact_name, contact_email, contact_phone, status
) VALUES (
    4,
    'MH-S2-SLOT6-RES01',
    3,
    6,
    4,
    'None',
    'Sprint2 Guest A',
    'guestA@example.com',
    '+39 340 0000001',
    'CONFIRMED'
);

-- Res 5: party 1 on T11 (4 - 1 = 3 free seats left on T11)
INSERT OR IGNORE INTO reservations (
    id, booking_reference, user_id, slot_id, party_size, special_requirements,
    contact_name, contact_email, contact_phone, status
) VALUES (
    5,
    'MH-S2-SLOT6-RES02',
    4,
    6,
    1,
    'None',
    'Sprint2 Guest B',
    'guestB@example.com',
    '+39 340 0000002',
    'CONFIRMED'
);

-- Res 6: party 1 on T12 (2 - 1 = 1 free seat left on T12)
INSERT OR IGNORE INTO reservations (
    id, booking_reference, user_id, slot_id, party_size, special_requirements,
    contact_name, contact_email, contact_phone, status
) VALUES (
    6,
    'MH-S2-SLOT6-RES03',
    5,
    6,
    1,
    'None',
    'Sprint2 Guest C',
    'guestC@example.com',
    '+39 340 0000003',
    'CONFIRMED'
);

-- Table assignments for Slot 6:
INSERT OR IGNORE INTO reservation_table_assignments (id, reservation_id, slot_table_id, assigned_seats) VALUES
(5, 4, 20, 4), -- T10 (slot_table 20): 4 seats taken -> 2 free
(6, 5, 21, 1), -- T11 (slot_table 21): 1 seat taken -> 3 free
(7, 6, 22, 1); -- T12 (slot_table 22): 1 seat taken -> 1 free
-- Resulting free seats in Slot 6: Table T10 (2), Table T11 (3), Table T12 (1) = 6 free seats!

-- --------------------------------------------------------------------
-- Confirmed Bookings for Slot 7 (Fully Booked)
-- --------------------------------------------------------------------
INSERT OR IGNORE INTO reservations (
    id, booking_reference, user_id, slot_id, party_size, special_requirements,
    contact_name, contact_email, contact_phone, status
) VALUES 
(7, 'MH-S2-SLOT7-RES01', 3, 7, 4, 'None', 'Full Party A', 'fullA@example.com', '+39 340 0000004', 'CONFIRMED'),
(8, 'MH-S2-SLOT7-RES02', 4, 7, 4, 'None', 'Full Party B', 'fullB@example.com', '+39 340 0000005', 'CONFIRMED');

INSERT OR IGNORE INTO reservation_table_assignments (id, reservation_id, slot_table_id, assigned_seats) VALUES
(8, 7, 23, 4), -- T13 100% full
(9, 8, 24, 4); -- T14 100% full

