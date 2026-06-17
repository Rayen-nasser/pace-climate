"""initial

Revision ID: 7fad641f4136
Revises: 
Create Date: 2026-06-17 22:31:00.910399

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '7fad641f4136'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER NOT NULL,
            email VARCHAR,
            username VARCHAR,
            password_hash VARCHAR,
            created_at DATETIME,
            PRIMARY KEY (id)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_users_email ON users (email)")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email_unique ON users (email)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_users_id ON users (id)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS user_preferences (
            user_id INTEGER NOT NULL,
            lat FLOAT,
            lon FLOAT,
            time_pref VARCHAR,
            temp_min INTEGER,
            temp_max INTEGER,
            FOREIGN KEY(user_id) REFERENCES users(id),
            PRIMARY KEY (user_id)
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS run_logs (
            id INTEGER NOT NULL,
            user_id INTEGER,
            date VARCHAR,
            distance_km FLOAT,
            duration_min INTEGER,
            rating INTEGER,
            avg_hr INTEGER,
            max_hr INTEGER,
            elevation_gain FLOAT,
            weather_snapshot TEXT,
            notes TEXT,
            tough_reasons TEXT,
            run_type VARCHAR,
            perceived_effort INTEGER,
            pre_run_energy INTEGER,
            sleep_hours FLOAT,
            muscle_soreness INTEGER,
            created_at DATETIME,
            FOREIGN KEY(user_id) REFERENCES users(id),
            PRIMARY KEY (id)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_run_logs_id ON run_logs (id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_run_logs_user_id ON run_logs (user_id)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS ml_models (
            user_id INTEGER NOT NULL,
            model_blob BLOB,
            trained_at DATETIME,
            run_count INTEGER,
            FOREIGN KEY(user_id) REFERENCES users(id),
            PRIMARY KEY (user_id)
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS user_goals (
            user_id INTEGER NOT NULL,
            weekly_distance_km FLOAT,
            weekly_runs INTEGER,
            created_at DATETIME,
            FOREIGN KEY(user_id) REFERENCES users(id),
            PRIMARY KEY (user_id)
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS device_tokens (
            id INTEGER NOT NULL,
            user_id INTEGER,
            token VARCHAR,
            platform VARCHAR,
            created_at DATETIME,
            FOREIGN KEY(user_id) REFERENCES users(id),
            PRIMARY KEY (id)
        )
    """)
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_device_tokens_token ON device_tokens (token)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_device_tokens_id ON device_tokens (id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_device_tokens_user_id ON device_tokens (user_id)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS scheduled_notifications (
            id INTEGER NOT NULL,
            user_id INTEGER,
            date VARCHAR,
            time VARCHAR,
            title VARCHAR,
            body VARCHAR,
            sent INTEGER,
            sent_at DATETIME,
            created_at DATETIME,
            FOREIGN KEY(user_id) REFERENCES users(id),
            PRIMARY KEY (id)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_scheduled_notifications_date ON scheduled_notifications (date)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_scheduled_notifications_id ON scheduled_notifications (id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_scheduled_notifications_user_id ON scheduled_notifications (user_id)")


def downgrade():
    op.drop_table('scheduled_notifications')
    op.drop_table('device_tokens')
    op.drop_table('user_goals')
    op.drop_table('ml_models')
    op.drop_table('run_logs')
    op.drop_table('user_preferences')
    op.drop_table('users')
