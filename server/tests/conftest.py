from __future__ import annotations

import os
import uuid
from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import Workspace
from app.db.session import Base


@pytest.fixture
def sqlite_session_factory(tmp_path) -> Generator[sessionmaker, None, None]:
    db_file = tmp_path / "token_budget_test.db"
    engine = create_engine(f"sqlite:///{db_file}", connect_args={"check_same_thread": False}, future=True)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
    Base.metadata.create_all(engine)
    try:
        yield SessionLocal
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture
def db_session(sqlite_session_factory: sessionmaker) -> Generator[Session, None, None]:
    session = sqlite_session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def workspace_id(db_session: Session) -> uuid.UUID:
    workspace = Workspace(name="Test Workspace", owner_id=uuid.uuid4())
    db_session.add(workspace)
    db_session.commit()
    return workspace.id


@pytest.fixture
def pg_session_factory() -> Generator[sessionmaker | None, None, None]:
    test_database_url = os.getenv("TEST_DATABASE_URL")
    if not test_database_url:
        yield None
        return

    engine = create_engine(test_database_url, pool_pre_ping=True, future=True)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
    Base.metadata.create_all(engine)
    try:
        yield SessionLocal
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()
