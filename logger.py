"""

Logging utilities for UPS monitor.

This module provides a single application logger.

The logger writes to:
    1. ./logs/ups.log
    2. stdout/stderr

Logging failures should never terminate the UPS monitor.

"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from config import APP_NAME, LOG_FILE

# ============================================================
# Constants
# ============================================================

LOG_LEVEL = logging.INFO

LOG_MAX_BYTES = 1 * 1024 * 1024 # 1 MB
LOG_BACKUP_COUNT = 3 # Keep 3 old log files

LOG_FORMAT = (
    "%(asctime)s"
    "[%(levelname)s]"
    "%(message)s"
)

DATE_FORMAT ="%Y-%m-%d %H:%M:%S"

# ============================================================
# Logger creation
# ============================================================

def _create_logger() -> logging.Logger:
    """
    Create and configure the application logger.

    Returns:
        logging.Logger: Configured UPS monitor logger.
    """

    logger = logging.getLogger(APP_NAME)

    # Prevent propagation to the root logger.
    #
    # Otherwise, if another logging configuration exists,
    # messages may be printed twice.
    logger.propagate = False

    # Avoid adding handlers multiple times.
    #
    # This is important if get_logger() is called more than once.
    if logger.handlers:
        return logger

    logger.setLevel(LOG_LEVEL)

    formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt=DATE_FORMAT)

    # ============================================================
    # File handler
    # ============================================================

    try:
        log_path = Path(LOG_FILE)

        # Create:
        #    ./logs/
        # if it does not already exist.
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = RotatingFileHandler(
            filename=log_path,
            maxBytes=LOG_MAX_BYTES,
            backupCount=LOG_BACKUP_COUNT,
            encoding="utf-8"
        )

        file_handler.setLevel(LOG_LEVEL)
        file_handler.setFormatter(formatter)

        logger.addHandler(file_handler)

    except Exception:
        # Logging failure must not stop the UPS monitor.
        #
        # For example:
        #   - disk full
        #   - permission denied
        #   - filesystem unavailable
        #
        print(
            f"WARNING: Cannot initialize log file: {LOG_FILE}",
            file=sys.stderr
        )

    # ============================================================
    # Console handler
    # ============================================================

    console_handler = logging.StreamHandler(sys.stdout)

    console_handler.setLevel(LOG_LEVEL)
    console_handler.setFormatter(formatter)

    logger.addHandler(console_handler)

    return logger

# ============================================================
# Public logger
# ============================================================

logger = _create_logger()