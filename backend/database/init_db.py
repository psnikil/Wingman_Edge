"""
This is for the manual startup of db
"""

from sqlalchemy import create_engine
from db_models import Base
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)

if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)

    print("Database and tables created")