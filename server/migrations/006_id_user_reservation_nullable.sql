PRAGMA foreign_keys = OFF;

BEGIN TRANSACTION;

-- 1. Create a temporary table with the updated structure
CREATE TABLE reservations_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    booking_reference VARCHAR(32) NOT NULL UNIQUE,
    user_id INTEGER,
    slot_id INTEGER NOT NULL,
    party_size INTEGER NOT NULL CHECK (party_size > 0),
    contact_name VARCHAR(200) NOT NULL,
    contact_email VARCHAR(255) NOT NULL,
    contact_phone VARCHAR(50),
    status VARCHAR(20) NOT NULL DEFAULT 'CONFIRMED',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_res_user
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,

    CONSTRAINT fk_res_slot
        FOREIGN KEY (slot_id) REFERENCES time_slots(id) ON DELETE CASCADE,

    CONSTRAINT uq_user_slot_reservation UNIQUE (user_id, slot_id),

    CONSTRAINT chk_res_status
        CHECK (status IN ('CONFIRMED', 'CANCELLED', 'COMPLETED', 'NO_SHOW'))
);

-- 2. Copy all existing records
INSERT INTO reservations_new (
    id,
    booking_reference,
    user_id,
    slot_id,
    party_size,
    contact_name,
    contact_email,
    contact_phone,
    status,
    created_at,
    updated_at
)
SELECT
    id,
    booking_reference,
    user_id,
    slot_id,
    party_size,
    contact_name,
    contact_email,
    contact_phone,
    status,
    created_at,
    updated_at
FROM reservations;

-- 3. Drop the old table
DROP TABLE reservations;

-- 4. Rename the new table
ALTER TABLE reservations_new RENAME TO reservations;

COMMIT;

PRAGMA foreign_keys = ON;