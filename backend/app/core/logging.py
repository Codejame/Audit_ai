"""Structured logging configuration for Document Intelligence Platform."""
import logging
import os
import sys
from typing import Optional

def setup_logging(level: Optional[str] = None) -> logging.Logger:
    """Configures application-wide structured logging."""
    log_level_str = (level or os.getenv("LOG_LEVEL", "INFO")).upper()
    log_level = getattr(logging, log_level_str, logging.INFO)

    log_format = (
        "%(asctime)s | %(levelname)-8s | [%(name)s:%(lineno)d] - %(message)s"
    )
    date_format = "%Y-%m-%d %H:%M:%S"

    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format=log_format,
        datefmt=date_format,
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )

    logger = logging.getLogger("document_intelligence")
    logger.setLevel(log_level)
    return logger

logger = setup_logging()
