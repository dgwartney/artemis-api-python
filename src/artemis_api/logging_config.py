"""Centralized logging configuration for artemis_api.

Provides a single named logger (``"artemis_api"``) with console and optional
rotating-file output, plus a filter that masks sensitive values (API keys,
long opaque tokens) before they reach any log sink.
"""

from __future__ import annotations

import json
import logging
import re
from logging.handlers import RotatingFileHandler
from pathlib import Path

SIMPLE_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

LOGGER_NAME = "artemis_api"
"""Name of the root logger used by this package."""

_MAX_LOG_FILE_BYTES = 10 * 1024 * 1024
_LOG_FILE_BACKUP_COUNT = 3


_TOKEN_RE = re.compile(r"[A-Za-z0-9_-]+")
_MIN_MASKED_TOKEN_LENGTH = 10
_MASKED_PREFIX_LENGTH = 4


def _mask_token_if_key_shaped(match: re.Match[str]) -> str:
    """Mask a single alnum/dash/underscore token if it looks like a key or opaque ID.

    A token is considered key-shaped if it's long enough and contains at
    least one digit -- this catches API keys, session IDs, and similar
    tokens while leaving ordinary alphabetic words (header names, log
    message text) untouched.

    Args:
        match: A regex match for one ``[A-Za-z0-9_-]+`` run.

    Returns:
        The masked token, or the original token if it isn't key-shaped.
    """
    token = match.group(0)
    if len(token) >= _MIN_MASKED_TOKEN_LENGTH and any(char.isdigit() for char in token):
        return f"{token[:_MASKED_PREFIX_LENGTH]}****"
    return token


def mask_sensitive_data(text: str) -> str:
    """Mask API keys and other opaque tokens in a string.

    Args:
        text: Text that may contain sensitive data.

    Returns:
        The input text with any recognizable secret values replaced by a
        masked placeholder that preserves a short, non-sensitive prefix.

    Examples:
        >>> mask_sensitive_data('x-api-key: "kg-abc1234567890"')
        'x-api-key: "kg-a****"'
    """
    return _TOKEN_RE.sub(_mask_token_if_key_shaped, text)


class SensitiveDataFilter(logging.Filter):
    """Logging filter that masks sensitive data in log records before they're emitted."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Mask sensitive data in the record's message and arguments.

        Args:
            record: The log record to filter in place.

        Returns:
            Always ``True``; this filter never drops records, it only redacts them.
        """
        record.msg = mask_sensitive_data(str(record.msg))

        if record.args:
            if isinstance(record.args, tuple):
                record.args = tuple(
                    mask_sensitive_data(arg) if isinstance(arg, str) else arg
                    for arg in record.args
                )
            elif isinstance(record.args, dict):
                record.args = {
                    key: mask_sensitive_data(value) if isinstance(value, str) else value
                    for key, value in record.args.items()
                }

        return True


def setup_logging(
    log_level: str = "WARNING",
    log_file: str | None = None,
    verbose: bool = False,
) -> logging.Logger:
    """Configure the ``artemis_api`` logger.

    Args:
        log_level: Logging level name (``DEBUG``, ``INFO``, ``WARNING``, ``ERROR``,
            ``CRITICAL``). Invalid names fall back to ``WARNING``.
        log_file: Optional path to a log file. If given, a rotating file handler
            (10 MB per file, 3 backups) is added in addition to the console handler.
        verbose: If ``True``, overrides ``log_level`` with ``DEBUG``.

    Returns:
        The configured ``artemis_api`` logger.
    """
    if verbose:
        log_level = "DEBUG"

    numeric_level = getattr(logging, log_level.upper(), logging.WARNING)

    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(numeric_level)
    logger.handlers.clear()
    logger.propagate = False

    formatter = logging.Formatter(SIMPLE_FORMAT, datefmt=DATE_FORMAT)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(SensitiveDataFilter())
    logger.addHandler(console_handler)

    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=_MAX_LOG_FILE_BYTES,
            backupCount=_LOG_FILE_BACKUP_COUNT,
            encoding="utf-8",
        )
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        file_handler.addFilter(SensitiveDataFilter())
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str | None = None) -> logging.Logger:
    """Get a logger under the ``artemis_api`` namespace.

    Args:
        name: Optional sub-logger name (e.g. ``"client"``). If omitted, the
            root ``artemis_api`` logger is returned.

    Returns:
        A :class:`logging.Logger` instance.
    """
    if name:
        return logging.getLogger(f"{LOGGER_NAME}.{name}")
    return logging.getLogger(LOGGER_NAME)


def log_api_request(url: str, method: str, body: dict | None = None) -> None:
    """Log an outgoing API request at INFO, with the body dumped at DEBUG.

    Args:
        url: The request URL.
        method: The HTTP method (e.g. ``"POST"``).
        body: The JSON-serializable request body, if any.
    """
    logger = get_logger("client")
    logger.info("%s request to %s", method, url)
    if body is not None and logger.isEnabledFor(logging.DEBUG):
        logger.debug("Request body: %s", json.dumps(body, indent=2))


def log_api_response(status_code: int, response_data: dict | None = None) -> None:
    """Log an API response at INFO, with the body dumped at DEBUG.

    Args:
        status_code: The HTTP status code received.
        response_data: The parsed JSON response body, if any.
    """
    logger = get_logger("client")
    logger.info("Response received: %s", status_code)
    if response_data is not None and logger.isEnabledFor(logging.DEBUG):
        logger.debug("Response data: %s", json.dumps(response_data, indent=2))
