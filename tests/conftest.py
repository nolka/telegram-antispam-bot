"""
Test fixtures for the project.

Uses testcontainers to spin up a temporary PostgreSQL container for tests.
Requires Docker to be running.
"""

import pytest
from testcontainers.postgres import PostgresContainer

from models import Base
from storage import DatabaseStorage


@pytest.fixture(scope="session")
def postgres_container():
    """Starts a PostgreSQL container for the test session."""
    with PostgresContainer("postgres:17-alpine") as postgres:
        yield postgres


@pytest.fixture(scope="session")
def postgres_url(postgres_container):
    """Returns SQLAlchemy-compatible PostgreSQL URL."""
    return postgres_container.get_connection_url()


@pytest.fixture
def db_storage(postgres_url):
    """Provides a fresh DatabaseStorage with clean tables for each test."""
    from sqlalchemy import create_engine

    engine = create_engine(postgres_url)
    Base.metadata.drop_all(engine)

    storage = DatabaseStorage(postgres_url)
    yield storage

    Base.metadata.drop_all(engine)
