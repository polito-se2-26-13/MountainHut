-- ====================================================================
-- Migration: 002_seed_data.sql
-- Description: Realistic seed data illustrating MH-01, MH-02, MH-03 and context.md
-- All user accounts default to password: Password123!
-- ====================================================================

-- --------------------------------------------------------------------
-- 1. Seed Hut Info
-- --------------------------------------------------------------------
INSERT OR IGNORE INTO hut_info (
    id, name, description, location, altitude_m, how_to_reach, points_of_interest,
    contact_email, contact_phone, has_ebike_charging
) VALUES (
    1,
    'Rifugio Alpe Grande',
    'Historic alpine hut situated at 2,150m, offering traditional mountain hospitality, warm meals, and panoramic views of the western Alps.',
    'Valle d''Aosta / Piedmont Western Alps',
    2150,
    'Trail 3A from the valley parking (approx. 2.5 hours hike, 750m elevation gain), or military gravel track suitable for mountain bikes.',
    'Monte Rosa viewpoint, Glacier tarn (45 min walk), Alpine botanical reserve.',
    'info@rifugioalpegrande.it',
    '+39 0125 987654',
    1
);

-- --------------------------------------------------------------------
-- 2. Seed Users (Warden, Employee, Hikers)
-- Password for all seed users is: Password123!
-- --------------------------------------------------------------------
INSERT OR IGNORE INTO users (
    id, email, password_hash, first_name, last_name, phone, role, notes, emergency_contact, is_active
) VALUES 
(
    1,
    'warden@mountainhut.com',
    '600310da4c63aeecbc3b40cc3c96d085$76ab5fae1ca88c390c151a9a3a8a848d557f5ec4684c7d853d0caf3640506a6c',
    'Marco',
    'Rossi',
    '+39 333 1112233',
    'Warden',
    'Hut Warden & Operations Lead',
    'Elena Rossi (+39 333 9998877)',
    1
),
(
    2,
    'employee@mountainhut.com',
    '600310da4c63aeecbc3b40cc3c96d085$76ab5fae1ca88c390c151a9a3a8a848d557f5ec4684c7d853d0caf3640506a6c',
    'Giulia',
    'Bianchi',
    '+39 333 4445566',
    'Employee',
    'Hut Staff & Service Coordinator',
    'Davide Bianchi (+39 333 5556677)',
    1
),
(
    3,
    'hiker1@example.com',
    '600310da4c63aeecbc3b40cc3c96d085$76ab5fae1ca88c390c151a9a3a8a848d557f5ec4684c7d853d0caf3640506a6c',
    'Alex',
    'Smith',
    '+39 340 1234567',
    'Hiker',
    'Registered mountain guide (UIAGM)',
    'Sarah Smith (+39 340 9876543)',
    1
),
(
    4,
    'hiker2@example.com',
    '600310da4c63aeecbc3b40cc3c96d085$76ab5fae1ca88c390c151a9a3a8a848d557f5ec4684c7d853d0caf3640506a6c',
    'Elena',
    'Moretti',
    '+39 349 2345678',
    'Hiker',
    'Frequent visitor, trail runner',
    'Luca Moretti (+39 349 8765432)',
    1
),
(
    5,
    'hiker3@example.com',
    '600310da4c63aeecbc3b40cc3c96d085$76ab5fae1ca88c390c151a9a3a8a848d557f5ec4684c7d853d0caf3640506a6c',
    'John',
    'Doe',
    '+39 348 3456789',
    'Hiker',
    'Travelling with family and hiking club',
    'Mary Doe (+39 348 7654321)',
    1
);

-- --------------------------------------------------------------------
-- 3. Seed Hut Tables (MH-01 & MH-02)
-- --------------------------------------------------------------------
INSERT OR IGNORE INTO tables (id, table_number, capacity, location, is_active) VALUES
(1, 'T1', 6, 'Indoor Main Hall', 1),
(2, 'T2', 4, 'Indoor Main Hall', 1),
(3, 'T3', 8, 'Indoor Main Hall', 1),
(4, 'T4', 4, 'Stube (Fireplace)', 1),
(5, 'T5', 6, 'Terrace (Panoramic)', 1),
(6, 'T6', 6, 'Terrace (Panoramic)', 1);

-- --------------------------------------------------------------------
-- 4. Seed Time Slots (MH-01 & MH-02: Lunch & Dinner flexible slots)
-- --------------------------------------------------------------------
INSERT OR IGNORE INTO time_slots (id, date, start_time, end_time, meal_type, status, notes, created_by_id) VALUES
(1, '2026-10-30', '12:00:00', '13:00:00', 'Lunch', 'OPEN', 'Lunch Service 1 - Sunny day seating active', 2),
(2, '2026-10-30', '13:00:00', '14:00:00', 'Lunch', 'OPEN', 'Lunch Service 2 - Sunny day seating active', 2),
(3, '2026-10-30', '19:00:00', '20:30:00', 'Dinner', 'OPEN', 'Dinner Service 1 - Indoor only', 2),
(4, '2026-10-30', '20:30:00', '22:00:00', 'Dinner', 'OPEN', 'Dinner Service 2 - Indoor only', 2);

-- --------------------------------------------------------------------
-- 5. Seed Slot Table Capacity (MH-02)
-- Demonstrating configurable sets: Lunch uses all tables (indoor + terrace),
-- while Dinner uses only indoor tables (T1..T4).
-- --------------------------------------------------------------------
-- Slot 1 (Lunch 1): Tables T1-T6 (total 34 seats)
INSERT OR IGNORE INTO slot_tables (id, slot_id, table_id, available_seats, is_available) VALUES
(1, 1, 1, 6, 1),
(2, 1, 2, 4, 1),
(3, 1, 3, 8, 1),
(4, 1, 4, 4, 1),
(5, 1, 5, 6, 1),
(6, 1, 6, 6, 1);

-- Slot 2 (Lunch 2): Tables T1-T6 (total 34 seats)
INSERT OR IGNORE INTO slot_tables (id, slot_id, table_id, available_seats, is_available) VALUES
(7,  2, 1, 6, 1),
(8,  2, 2, 4, 1),
(9,  2, 3, 8, 1),
(10, 2, 4, 4, 1),
(11, 2, 5, 6, 1),
(12, 2, 6, 6, 1);

-- Slot 3 (Dinner 1): Tables T1-T4 (indoor only, total 22 seats)
INSERT OR IGNORE INTO slot_tables (id, slot_id, table_id, available_seats, is_available) VALUES
(13, 3, 1, 6, 1),
(14, 3, 2, 4, 1),
(15, 3, 3, 8, 1),
(16, 3, 4, 4, 1);

-- --------------------------------------------------------------------
-- 6. Seed Reservations (MH-01 & MH-03)
-- --------------------------------------------------------------------
-- Res 1: Alex Smith, party of 4 in Slot 1
INSERT OR IGNORE INTO reservations (
    id, booking_reference, user_id, slot_id, party_size, special_requirements,
    contact_name, contact_email, contact_phone, status
) VALUES (
    1,
    'MH-20261030-ALX01',
    3,
    1,
    4,
    '2 vegetarian meals, 1 gluten allergy',
    'Alex Smith',
    'hiker1@example.com',
    '+39 340 1234567',
    'CONFIRMED'
);

-- Res 2: Elena Moretti, party of 2 in Slot 1 (sharing Table T1 with Alex Smith!)
INSERT OR IGNORE INTO reservations (
    id, booking_reference, user_id, slot_id, party_size, special_requirements,
    contact_name, contact_email, contact_phone, status
) VALUES (
    2,
    'MH-20261030-ELN02',
    4,
    1,
    2,
    'High chair requested for toddler',
    'Elena Moretti',
    'hiker2@example.com',
    '+39 349 2345678',
    'CONFIRMED'
);

-- Res 3: John Doe, party of 10 in Slot 2 (party size exceeds single table capacity -> split across T3 and T2!)
INSERT OR IGNORE INTO reservations (
    id, booking_reference, user_id, slot_id, party_size, special_requirements,
    contact_name, contact_email, contact_phone, status
) VALUES (
    3,
    'MH-20261030-JHN03',
    5,
    2,
    10,
    'Mountain hiking club group',
    'John Doe',
    'hiker3@example.com',
    '+39 348 3456789',
    'CONFIRMED'
);

-- --------------------------------------------------------------------
-- 7. Seed Reservation Table Assignments (MH-01)
-- Demonstrating Table Sharing:
-- Res 1 (party 4) is assigned 4 seats at Table T1 (slot_table_id 1)
-- Res 2 (party 2) is assigned 2 seats at Table T1 (slot_table_id 1)
-- Table T1 capacity is 6, now fully shared by Res 1 and Res 2!
-- Demonstrating Party Splitting:
-- Res 3 (party 10) is split: 8 seats at Table T3 (slot_table_id 9) + 2 seats at Table T2 (slot_table_id 8)
-- --------------------------------------------------------------------
INSERT OR IGNORE INTO reservation_table_assignments (id, reservation_id, slot_table_id, assigned_seats) VALUES
(1, 1, 1, 4),
(2, 2, 1, 2),
(3, 3, 9, 8),
(4, 3, 8, 2);

