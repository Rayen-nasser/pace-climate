"""One-time script: migrate data from SQLite to Supabase PostgreSQL.

Usage:
    python scripts/migrate_to_pg.py <sqlite_url> <postgres_url>

Example:
    python scripts/migrate_to_pg.py sqlite:///./paceclimate.db postgresql://postgres:pass@db.xxx.supabase.co:5432/postgres
"""
import sys
from sqlalchemy import create_engine, MetaData, text
from sqlalchemy.orm import sessionmaker


def get_table_order():
    """Tables in dependency order (parents first)."""
    return [
        "users",
        "user_preferences",
        "run_logs",
        "ml_models",
        "user_goals",
        "device_tokens",
        "scheduled_notifications",
    ]


def get_indexes(meta, table_name):
    """Get non-PK indexes for a table."""
    table = meta.tables[table_name]
    indexes = []
    for idx in table.indexes:
        cols = [c.name for c in idx.columns]
        if cols != [pk.name for pk in table.primary_key.columns]:
            indexes.append((idx.name, cols, idx.unique))
    return indexes


def migrate(sqlite_url: str, pg_url: str):
    sqlite_engine = create_engine(sqlite_url)
    pg_engine = create_engine(pg_url)

    sqlite_meta = MetaData()
    sqlite_meta.reflect(bind=sqlite_engine)
    pg_meta = MetaData()
    pg_meta.reflect(bind=pg_engine)

    SqliteSession = sessionmaker(bind=sqlite_engine)
    PgSession = sessionmaker(bind=pg_engine)

    table_order = get_table_order()

    for table_name in table_order:
        if table_name not in sqlite_meta.tables:
            print(f"  SKIP {table_name} — not found in source")
            continue
        if table_name not in pg_meta.tables:
            print(f"  SKIP {table_name} — not found in target")
            continue

        src_table = sqlite_meta.tables[table_name]
        dst_table = pg_meta.tables[table_name]

        sqlite_session = SqliteSession()
        pg_session = PgSession()

        try:
            rows = sqlite_session.execute(src_table.select()).fetchall()
            if not rows:
                print(f"  {table_name}: 0 rows (empty)")
                continue

            col_names = [c.name for c in src_table.columns]
            insert = dst_table.insert().values([dict(zip(col_names, row)) for row in rows])
            pg_session.execute(insert)
            pg_session.commit()
            print(f"  {table_name}: {len(rows)} rows migrated")
        except Exception as e:
            pg_session.rollback()
            print(f"  {table_name}: ERROR — {e}")
        finally:
            sqlite_session.close()
            pg_session.close()

    print("\nDone. Verify data in Supabase, then set DATABASE_URL env var and redeploy.")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python scripts/migrate_to_pg.py <sqlite_url> <postgres_url>")
        sys.exit(1)
    migrate(sys.argv[1], sys.argv[2])
