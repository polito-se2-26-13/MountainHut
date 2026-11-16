"""Integration tests for database migrations and seed data."""

import pytest
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import create_async_engine
import pytest_asyncio
from server.database import set_sqlite_pragma
from server.scripts.db_setup import run_migrations, seed_db


@pytest.mark.asyncio
async def test_database_migrations_and_seed_data(tmp_path):
    """Test database creation, migrations, seed data and idempotency."""

    # Create an isolated temporary database
    db_path = tmp_path / "test_seed.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")

    # Enable SQLite foreign key constraints
    event.listen(engine.sync_engine, "connect", set_sqlite_pragma)

    try:
        # 1. Run database migrations
        applied = await run_migrations(engine)

        assert "001_initial_schema.sql" in applied
        assert "002_seed_data.sql" in applied

        # 2. Check that all expected tables exist
        async with engine.connect() as conn:
            result = await conn.execute(
                text("""
                    SELECT name
                    FROM sqlite_master
                    WHERE type = 'table'
                """)
            )
            table_names = {row[0] for row in result.fetchall()}

            expected_tables = {
                "schema_migrations",
                "hut_info",
                "users",
                "tables",
                "time_slots",
                "slot_tables",
                "reservations",
                "reservation_table_assignments",
            }

            assert expected_tables.issubset(table_names)

            # 3. Check the number of seeded records
            expected_counts = {
                "hut_info": 1,
                "users": 5,
                "tables": 6,
                "time_slots": 4,
                "slot_tables": 16,
                "reservations": 3,
                "reservation_table_assignments": 4,
            }

            for table, expected in expected_counts.items():
                result = await conn.execute(
                    text(f"SELECT COUNT(*) FROM {table}")
                )
                assert result.scalar_one() == expected

            # 4. Check user roles
            result = await conn.execute(
                text("""
                    SELECT role, COUNT(*)
                    FROM users
                    GROUP BY role
                """)
            )
            roles = dict(result.fetchall())

            assert roles == {
                "Warden": 1,
                "Employee": 1,
                "Hiker": 3,
            }

            # 5. Check reservation seat assignments
            result = await conn.execute(
                text("""
                    SELECT reservation_id, SUM(assigned_seats)
                    FROM reservation_table_assignments
                    GROUP BY reservation_id
                """)
            )
            assignments = dict(result.fetchall())

            assert assignments == {
                1: 4,
                2: 2,
                3: 10,
            }

            # 6. Check migration tracking
            result = await conn.execute(
                text("SELECT version FROM schema_migrations")
            )
            versions = {row[0] for row in result.fetchall()}

            assert "001_initial_schema.sql" in versions
            assert "002_seed_data.sql" in versions

            # 7. Check foreign key integrity
            result = await conn.execute(
                text("PRAGMA foreign_key_check")
            )
            assert result.fetchall() == []

        # 8. Check that migrations are not applied twice
        applied_again = await run_migrations(engine)
        assert applied_again == []

        # 9. Check that seeding does not create duplicate records
        await seed_db(engine)

        async with engine.connect() as conn:
            for table, expected in expected_counts.items():
                result = await conn.execute(
                    text(f"SELECT COUNT(*) FROM {table}")
                )
                assert result.scalar_one() == expected

    finally:
        await engine.dispose()
@pytest_asyncio.fixture
async def seeded_engine(tmp_path):
    """Create a temporary database with migrations and seed data."""

    db_path = tmp_path / "test_relationships.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")

    event.listen(engine.sync_engine, "connect", set_sqlite_pragma)

    await run_migrations(engine)

    try:
        yield engine
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_seed_time_slot_table_relationships(seeded_engine):
    """Check tables and seat capacities assigned to each time slot."""

    async with seeded_engine.connect() as conn:
        result = await conn.execute(
            text("""
                SELECT
                    st.slot_id,
                    t.table_number,
                    st.available_seats
                FROM slot_tables st
                JOIN tables t ON st.table_id = t.id
                ORDER BY st.slot_id, t.id
            """)
        )

        rows = result.fetchall()

    actual = {}
    for slot_id, table_number, seats in rows:
        actual.setdefault(slot_id, {})[table_number] = seats

    expected = {
        1: {"T1": 6, "T2": 4, "T3": 8, "T4": 4, "T5": 6, "T6": 6},
        2: {"T1": 6, "T2": 4, "T3": 8, "T4": 4, "T5": 6, "T6": 6},
        3: {"T1": 6, "T2": 4, "T3": 8, "T4": 4},
    }

    assert actual == expected


@pytest.mark.asyncio
async def test_seed_reservation_relationships(seeded_engine):
    """Check reservation users, time slots, party sizes and statuses."""

    async with seeded_engine.connect() as conn:
        result = await conn.execute(
            text("""
                SELECT
                    r.id,
                    u.first_name,
                    u.last_name,
                    r.user_id,
                    r.slot_id,
                    r.party_size,
                    r.status
                FROM reservations r
                JOIN users u ON r.user_id = u.id
                ORDER BY r.id
            """)
        )

        reservations = result.fetchall()

    actual = [
        (
            row[0], row[1], row[2],
            row[3], row[4], row[5], row[6]
        )
        for row in reservations
    ]

    expected = [
        (1, "Alex", "Smith", 3, 1, 4, "CONFIRMED"),
        (2, "Elena", "Moretti", 4, 1, 2, "CONFIRMED"),
        (3, "John", "Doe", 5, 2, 10, "CONFIRMED"),
    ]

    assert actual == expected


@pytest.mark.asyncio
async def test_seed_reservation_assignments(seeded_engine):
    """Check table sharing, party splitting and assigned seat totals."""

    async with seeded_engine.connect() as conn:
        result = await conn.execute(
            text("""
                SELECT
                    rta.reservation_id,
                    t.table_number,
                    rta.assigned_seats
                FROM reservation_table_assignments rta
                JOIN slot_tables st ON rta.slot_table_id = st.id
                JOIN tables t ON st.table_id = t.id
                ORDER BY rta.reservation_id, t.id
            """)
        )

        rows = result.fetchall()

    actual = {
        reservation_id: {}
        for reservation_id in (1, 2, 3)
    }

    for reservation_id, table_number, seats in rows:
        actual[reservation_id][table_number] = seats

    expected = {
        1: {"T1": 4},
        2: {"T1": 2},
        3: {"T2": 2, "T3": 8},
    }

    assert actual == expected

    # Check that assigned seats equal each reservation's party size
    async with seeded_engine.connect() as conn:
        result = await conn.execute(
            text("""
                SELECT
                    r.id,
                    r.party_size,
                    COALESCE(SUM(rta.assigned_seats), 0)
                FROM reservations r
                LEFT JOIN reservation_table_assignments rta
                    ON r.id = rta.reservation_id
                GROUP BY r.id, r.party_size
                ORDER BY r.id
            """)
        )

        seat_totals = result.fetchall()

    for reservation_id, party_size, assigned_seats in seat_totals:
        assert assigned_seats == party_size

    # T1 is shared by two reservations, with all 6 seats allocated
    assert actual[1]["T1"] + actual[2]["T1"] == 6

    # John Doe's 10 people are split across T3 and T2
    assert actual[3]["T3"] + actual[3]["T2"] == 10
@pytest.mark.asyncio
async def test_seed_data_business_integrity(seeded_engine):
    """Seeded users, reservations and table assignments satisfy business constraints."""
    async with seeded_engine.connect() as conn:
        # Seeded users must have unique, non-empty email addresses and password hashes.
        result = await conn.execute(text("""
            SELECT
                COUNT(*) AS total_users,
                COUNT(DISTINCT email) AS unique_emails,
                SUM(CASE WHEN email IS NULL OR TRIM(email) = '' THEN 1 ELSE 0 END),
                SUM(CASE WHEN password_hash IS NULL OR TRIM(password_hash) = '' THEN 1 ELSE 0 END)
            FROM users
        """))
        total, unique_emails, empty_emails, empty_hashes = result.one()
        assert total == unique_emails
        assert empty_emails == 0
        assert empty_hashes == 0

        # Every reservation must have a valid user and time slot.
        result = await conn.execute(text("""
            SELECT COUNT(*)
            FROM reservations r
            LEFT JOIN users u ON u.id = r.user_id
            LEFT JOIN time_slots ts ON ts.id = r.slot_id
            WHERE u.id IS NULL OR ts.id IS NULL
        """))
        assert result.scalar_one() == 0

        # Every assignment must link to a reservation and a configured slot table.
        result = await conn.execute(text("""
            SELECT COUNT(*)
            FROM reservation_table_assignments rta
            LEFT JOIN reservations r ON r.id = rta.reservation_id
            LEFT JOIN slot_tables st ON st.id = rta.slot_table_id
            WHERE r.id IS NULL OR st.id IS NULL OR rta.assigned_seats <= 0
        """))
        assert result.scalar_one() == 0

        # A slot-table configuration cannot offer more seats than its physical table.
        result = await conn.execute(text("""
            SELECT COUNT(*)
            FROM slot_tables st
            JOIN tables t ON t.id = st.table_id
            WHERE st.available_seats > t.capacity OR st.available_seats < 0
        """))
        assert result.scalar_one() == 0

        # A reservation's assigned seats must not exceed the configured capacity
        # of the slot table it uses.
        result = await conn.execute(text("""
            SELECT COUNT(*)
            FROM reservation_table_assignments rta
            JOIN slot_tables st ON st.id = rta.slot_table_id
            WHERE rta.assigned_seats > st.available_seats
        """))
        assert result.scalar_one() == 0
