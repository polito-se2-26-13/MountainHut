-- ====================================================================
-- Migration: 005_drop_old_special_requirements.sql
-- Description: MH-05 the requirements are only in their table
-- ====================================================================

-- The free text of sprint 1 is no longer written or read: 004 already copied it
-- into special_requirements, one row per booking that had one
ALTER TABLE reservations DROP COLUMN special_requirements;
