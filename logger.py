"""
Logging facilities
"""

import logging
import sys


class Logger:
    """Simple logger class."""

    def __init__(self, logger_name: str, log_level: int = logging.INFO) -> None:
        log = logging.getLogger(logger_name)
        log.setLevel(log_level)

        handler = logging.StreamHandler(sys.stdout)

        formatter = logging.Formatter(
            "%(asctime)s - [%(levelname)s] %(name)s: %(message)s"
        )
        handler.setFormatter(formatter)
        log.addHandler(handler)
        self._log = log

    def info(self, message: str) -> None:
        """Logs informational message."""
        self._log.info(message)

    def error(self, message: str) -> None:
        """Logs error message."""
        self._log.error(message)
