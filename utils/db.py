"""Database utilities."""

import os


def get_postgres_dsn() -> str | None:
    """
    Build PostgreSQL DSN from environment variables.

    Priority:
    1. POSTGRES_DSN (if set directly)
    2. Assembled from POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB, POSTGRES_HOST, POSTGRES_PORT
    """
    db_url = os.getenv("POSTGRES_DSN")
    if db_url:
        return db_url

    user = os.getenv("POSTGRES_USER")
    password = os.getenv("POSTGRES_PASSWORD")
    db_name = os.getenv("POSTGRES_DB")

    if user and password and db_name:
        host = os.getenv("POSTGRES_HOST", "localhost")
        port = os.getenv("POSTGRES_PORT", "5432")
        return f"postgresql://{user}:{password}@{host}:{port}/{db_name}"

    return None
