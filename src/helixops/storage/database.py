"""Database connection and session management."""

from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from helixops.storage.models import Base


class DatabaseConnection:
    """Manages database connection and session lifecycle."""

    def __init__(self, db_url: str = "sqlite:///helixops.db", echo: bool = False):
        """Initialize database connection.

        Args:
            db_url: SQLAlchemy database URL
            echo: Enable SQL logging
        """
        self.db_url = db_url
        self.echo = echo

        # Create engine (use check_same_thread=False for SQLite)
        if "sqlite" in db_url:
            self.engine: Engine = create_engine(
                db_url,
                echo=echo,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
            )
        else:
            self.engine = create_engine(db_url, echo=echo)

        # Enable foreign keys for SQLite
        if "sqlite" in db_url:

            @event.listens_for(Engine, "connect")
            def set_sqlite_pragma(dbapi_conn: Any, connection_record: Any) -> None:
                cursor = dbapi_conn.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()

        self.SessionLocal = sessionmaker(bind=self.engine)
        self._create_tables()

    def _create_tables(self) -> None:
        """Create all tables if they don't exist."""
        Base.metadata.create_all(self.engine)

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Get a database session context manager."""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_session_no_commit(self) -> Session:
        """Get a database session without auto-commit."""
        return self.SessionLocal()

    def close(self) -> None:
        """Close the database connection."""
        self.engine.dispose()
