"""
Manual DB init: ``uv run python -m backend.database.init_db`` from repo root.
"""

import os

from dotenv import load_dotenv
from sqlalchemy import create_engine

from backend.database.db_models import Base

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise SystemExit("DATABASE_URL is not set")

engine = create_engine(DATABASE_URL)

if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    print("Database tables created.")
