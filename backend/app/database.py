"""Database configuration and session management"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .config import settings
from .core.security import encrypt_router_password, is_encrypted_router_password

# Create database engine
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False}  # Needed for SQLite
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)

    # Add missing columns for existing databases (SQLite migration)
    from sqlalchemy import text
    with engine.connect() as conn:
        # Check and add current_message column to tasks table
        try:
            conn.execute(text("ALTER TABLE tasks ADD COLUMN current_message VARCHAR(500)"))
            conn.commit()
        except Exception:
            pass  # Column already exists

    # Encrypt legacy plaintext router passwords in place.
    from .models.router import Router

    db = SessionLocal()
    try:
        routers = db.query(Router).all()
        changed = False
        for router in routers:
            stored_password = router._password
            if stored_password and not is_encrypted_router_password(stored_password):
                router._password = encrypt_router_password(stored_password)
                changed = True
        if changed:
            db.commit()
    finally:
        db.close()
