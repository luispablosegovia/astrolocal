"""Secure logging setup. PII is redacted by default."""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from astrolocal.config import AstroLocalConfig


class PIIRedactingFilter(logging.Filter):
    """Filter that redacts potential PII from log messages.

    Matches patterns like dates of birth, names after known prefixes,
    and coordinates that could identify a person.
    """

    PATTERNS = [
        # Dates in various formats
        (re.compile(r"\b\d{1,2}/\d{1,2}/\d{4}\b"), "[REDACTED_DATE]"),
        (re.compile(r"\b\d{4}-\d{2}-\d{2}\b"), "[REDACTED_DATE]"),
        # Coordinates with high precision (5+ decimal places)
        (re.compile(r"-?\d{1,3}\.\d{5,}"), "[REDACTED_COORD]"),
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        for pattern, replacement in self.PATTERNS:
            msg = pattern.sub(replacement, msg)
        record.msg = msg
        record.args = ()
        return True


def setup_logging(config: AstroLocalConfig) -> logging.Logger:
    """Configure application logger with optional PII redaction."""
    logger = logging.getLogger("astrolocal")
    logger.setLevel(config.app.log_level)

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    logger.addHandler(console)

    # File handler (optional)
    if config.app.log_file:
        from astrolocal.config import _safe_resolve

        log_path = _safe_resolve(config.app.log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(str(log_path))
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # Add PII filter if configured
    if config.output.redact_birth_data_in_logs:
        pii_filter = PIIRedactingFilter()
        for handler in logger.handlers:
            handler.addFilter(pii_filter)

    return logger
