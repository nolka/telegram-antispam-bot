"""
Logging facilities
"""

import logging
import sys


class Logger:
    def __init__(self, logger_name: str, log_level: int = logging.INFO) -> None:
        log = logging.getLogger(logger_name)
        log.setLevel(log_level)

        handler = logging.StreamHandler(sys.stdout)

        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        log.addHandler(handler)
        self._log = log

    def info(self, message: str, module_name: str = "") -> None:
        self._log.info(f"{module_name}: {message}")

    def error(self, message: str, module_name: str = "") -> None:
        self._log.error(f"{module_name}: {message}")
