from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from .config import DATABASE_URL

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    import os, sys
    ini_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "alembic.ini")
    if os.path.exists(ini_path):
        try:
            from alembic.config import Config
            from alembic import command
            cfg = Config(ini_path)
            command.upgrade(cfg, "head")
            print(f"Database migrated (alembic): {DATABASE_URL.split('://')[0]}://...")
            return
        except Exception as e:
            print(f"Alembic migration failed ({e}), falling back to create_all", file=sys.stderr)
    import app.models
    Base.metadata.create_all(bind=engine)
