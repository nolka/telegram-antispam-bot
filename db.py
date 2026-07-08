from threading import Lock

from sqlalchemy import create_engine
from sqlalchemy.orm import Session


class Connection:
    def __init__(self, db_url: str) -> None:
        self.engine = create_engine(db_url)
        self.mutex = Lock()

    def new_session(self) -> Session:
        """Create a new SQLAlchemy session (mutex-protected)."""
        with self.mutex:
            return Session(self.engine)
