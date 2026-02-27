import os
import ssl
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

DATABASE_URL = os.getenv("DATABASE_URL")

# SQLite fix for multi-threading
connect_args = {}

if not DATABASE_URL:
    DATABASE_URL = "sqlite:///:memory:"
    connect_args = {"check_same_thread": False}

# Vercel/Serverless Fix: Use pg8000 (pure python) for stability
if DATABASE_URL.startswith("postgres://") or DATABASE_URL.startswith("postgresql://"):
    # Ensure it uses the postgresql+pg8000 dialect
    if "postgresql+pg8000" not in DATABASE_URL:
        if DATABASE_URL.startswith("postgresql://"):
            DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+pg8000://", 1)
        else:
            DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+pg8000://", 1)
    
    # Strip query parameters that pg8000 connect() doesn't understand (like sslmode)
    if "?" in DATABASE_URL:
        DATABASE_URL = DATABASE_URL.split("?")[0]
    
    # Enable SSL for Neon using pg8000 compatible ssl_context
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    connect_args["ssl_context"] = ssl_context

try:
    engine = create_engine(DATABASE_URL, connect_args=connect_args)
except Exception as e:
    print(f"Warning: Failed to create engine for {DATABASE_URL}: {e}")
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
