"""
Shared pytest fixtures for the backend test suite.

Note: `app.main` executes raw Postgres-specific SQL (ALTER TABLE ... ADD COLUMN
IF NOT EXISTS, an UPDATE ... FROM backfill) at module-import time against the
configured `engine`. That SQL is not valid against SQLite, so tests must NOT
import `app.main`. Instead we build a slim, test-only FastAPI app here that
only creates tables via `Base.metadata.create_all(...)` and includes the
`tournaments` router - the same router `app.main` mounts.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import Base, get_db
from app.models import models  # noqa: F401  (ensure models are registered on Base)
from app.routers import tournaments


@pytest.fixture()
def db_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture()
def db_session(db_engine):
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def app(db_engine):
    """A slim test FastAPI app that mirrors app.main without the Postgres-only migration block."""
    test_app = FastAPI(title="Jass Turnier Verwaltung (test)")
    test_app.include_router(tournaments.router)

    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    test_app.dependency_overrides[get_db] = override_get_db
    return test_app


@pytest.fixture()
def client(app):
    return TestClient(app)
