"""
utils/logger.py
---------------
Centralized logger for the Fact-Check Agent.
Every module does: from utils.logger import get_logger; logger = get_logger(__name__)
Outputs timestamped logs to console (and optionally a file).
"""

import logging
import sys
from typing import Optional


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Get a named logger with consistent formatting.
    Uses the module __name__ as the logger name for clean traceability.

    Usage:
        from utils.logger import get_logger
        logger = get_logger(__name__)
        logger.info("PDF extracted: 3 pages")
        logger.error("Tavily search failed: timeout")
    """
    logger = logging.getLogger(name)

    # Avoid adding duplicate handlers if logger already configured
    if logger.handlers:
        return logger

    logger.setLevel(level)

    # Console handler — always on
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger