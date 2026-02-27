import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./todosapp.db")

# Vercel/Serverless Fix: Use pg8000 (pure python) if psycopg2 fails or explicitly
if DATABASE_URL.startswith("postgres://") or DATABASE_URL.startswith("postgresql://"):
    # Ensure it uses the postgresql+pg8000 dialect for best compatibility on Vercel
    if "postgresql+pg8000" not in DATABASE_URL:
        # Replace either postgresql:// or postgres:// with postgresql+pg8000://
        if DATABASE_URL.startswith("postgresql://"):
            DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+pg8000://", 1)
        else:
            DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+pg8000://", 1)

# SQLite fix for multi-threading
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, connect_args=connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
