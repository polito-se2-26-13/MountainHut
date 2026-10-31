"""Database setup, migration runner, and seed utility for MountainHut (Async)."""
import argparse
import asyncio
from pathlib import Path
from typing import List

from sqlalchemy import text, inspect
from server.database import engine, Base
import server.models.DAO  # noqa: F401 - ensure all ORM models are registered

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"


async def ensure_migrations_table(connection):
    """Ensure the schema_migrations tracking table exists."""
    await connection.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version VARCHAR(100) PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
    )


async def get_applied_migrations(connection) -> set:
    """Return set of applied migration version filenames."""
    await ensure_migrations_table(connection)
    result = await connection.execute(text("SELECT version FROM schema_migrations"))
    return {row[0] for row in result.fetchall()}


async def record_migration(connection, version: str):
    """Record an applied migration version."""
    await connection.execute(
        text("INSERT INTO schema_migrations (version) VALUES (:version)"),
        {"version": version},
    )


async def run_sql_script(connection, script_path: Path):
    """Execute a raw SQL script containing multiple statements asynchronously."""
    with open(script_path, "r", encoding="utf-8") as f:
        sql_content = f.read()

    raw_conn = await connection.get_raw_connection()
    await raw_conn.driver_connection.executescript(sql_content)


async def run_migrations(target_engine=None) -> List[str]:
    """Apply all pending SQL migrations in sorted order."""
    eng = target_engine or engine
    applied_now = []

    if not MIGRATIONS_DIR.exists():
        print(f"[db_setup] Migrations directory '{MIGRATIONS_DIR}' not found.")
        return applied_now

    sql_files = sorted(MIGRATIONS_DIR.glob("*.sql"))

    async with eng.begin() as conn:
        applied_versions = await get_applied_migrations(conn)

        for sql_file in sql_files:
            version_name = sql_file.name
            if version_name not in applied_versions:
                print(f"[db_setup] Applying migration: {version_name}...")
                await run_sql_script(conn, sql_file)
                await record_migration(conn, version_name)
                applied_now.append(version_name)
                print(f"[db_setup] Applied: {version_name}")
            else:
                print(f"[db_setup] Already applied: {version_name}")

    return applied_now


async def init_db(target_engine=None):
    """Create all ORM tables using SQLAlchemy Base metadata."""
    eng = target_engine or engine
    print("[db_setup] Creating all tables from SQLAlchemy models...")
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await ensure_migrations_table(conn)
    print("[db_setup] Tables created successfully.")


async def seed_db(target_engine=None):
    """Seed the database using 002_seed_data.sql."""
    eng = target_engine or engine
    seed_file = MIGRATIONS_DIR / "002_seed_data.sql"
    if not seed_file.exists():
        print(f"[db_setup] Seed file '{seed_file}' not found.")
        return

    async with eng.begin() as conn:
        applied_versions = await get_applied_migrations(conn)
        print(f"[db_setup] Seeding database with {seed_file.name}...")
        await run_sql_script(conn, seed_file)
        if seed_file.name not in applied_versions:
            await record_migration(conn, seed_file.name)
    print("[db_setup] Database seeded successfully.")


async def reset_db(target_engine=None, seed: bool = True):
    """Drop all tables, re-run schema creation / migrations, and optionally seed."""
    eng = target_engine or engine
    print("[db_setup] Dropping all tables...")
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.execute(text("DROP TABLE IF EXISTS schema_migrations;"))
    print("[db_setup] All tables dropped.")

    await run_migrations(eng)
    if seed:
        await seed_db(eng)
    print("[db_setup] Reset complete.")


async def check_status(target_engine=None):
    """Print the database schema status and record counts."""
    eng = target_engine or engine
    async with eng.connect() as conn:
        table_names = await conn.run_sync(
            lambda sync_conn: sorted(inspect(sync_conn).get_table_names())
        )

        print("\n=== MountainHut Database Status (Async) ===")
        print(f"Target Database URL: {eng.url}")
        print(f"Total Tables: {len(table_names)}\n")

        applied_migrations = await get_applied_migrations(conn)
        print(f"Applied Migrations ({len(applied_migrations)}):")
        for m in sorted(applied_migrations):
            print(f"  - {m}")
        print()

        print("Table Row Counts:")
        for table in table_names:
            try:
                count_res = await conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = count_res.scalar()
                print(f"  - {table:<30}: {count} rows")
            except Exception as e:
                print(f"  - {table:<30}: Error ({e})")
        print("===========================================\n")


def main():
    parser = argparse.ArgumentParser(description="MountainHut Database Setup & Migration Utility")
    parser.add_argument(
        "action",
        choices=["init", "migrate", "seed", "reset", "status"],
        help="Action to perform: init (create tables), migrate (run pending .sql), seed, reset, status",
    )
    parser.add_argument(
        "--no-seed",
        action="store_true",
        help="Skip seeding when resetting",
    )

    args = parser.parse_args()

    if args.action == "init":
        asyncio.run(init_db())
    elif args.action == "migrate":
        asyncio.run(run_migrations())
    elif args.action == "seed":
        asyncio.run(seed_db())
    elif args.action == "reset":
        asyncio.run(reset_db(seed=not args.no_seed))
    elif args.action == "status":
        asyncio.run(check_status())


if __name__ == "__main__":
    main()
