"""Tests for artemis_api.logging_config."""

import logging

from artemis_api.logging_config import (
    LOGGER_NAME,
    SensitiveDataFilter,
    get_logger,
    log_api_request,
    log_api_response,
    mask_sensitive_data,
    setup_logging,
)


def test_mask_sensitive_data_masks_long_quoted_tokens():
    text = 'x-api-key: "abcdefghijklmnopqrstuvwxyz123456"'
    assert mask_sensitive_data(text) == 'x-api-key: "abcdefgh****"'


def test_mask_sensitive_data_leaves_short_strings_alone():
    text = 'name: "short"'
    assert mask_sensitive_data(text) == text


def test_setup_logging_default_level_is_warning():
    logger = setup_logging()
    assert logger.name == LOGGER_NAME
    assert logger.level == logging.WARNING
    assert logger.propagate is False


def test_setup_logging_verbose_forces_debug():
    logger = setup_logging(verbose=True)
    assert logger.level == logging.DEBUG


def test_setup_logging_invalid_level_falls_back_to_warning():
    logger = setup_logging(log_level="not-a-level")
    assert logger.level == logging.WARNING


def test_setup_logging_clears_previous_handlers():
    setup_logging(log_level="INFO")
    first_handlers = list(logging.getLogger(LOGGER_NAME).handlers)
    setup_logging(log_level="INFO")
    second_handlers = list(logging.getLogger(LOGGER_NAME).handlers)
    assert len(second_handlers) == len(first_handlers)
    assert second_handlers[0] is not first_handlers[0]


def test_setup_logging_with_log_file_adds_file_handler(tmp_path):
    log_file = tmp_path / "nested" / "artemis.log"
    logger = setup_logging(log_level="DEBUG", log_file=str(log_file))
    logger.debug("hello")
    assert log_file.exists()
    assert len(logger.handlers) == 2


def test_get_logger_without_name_returns_root_logger():
    assert get_logger() is logging.getLogger(LOGGER_NAME)


def test_get_logger_with_name_returns_child_logger():
    child = get_logger("client")
    assert child.name == f"{LOGGER_NAME}.client"


def test_sensitive_data_filter_masks_msg_and_tuple_args(caplog):
    logger = logging.getLogger("test.filter.tuple")
    logger.addFilter(SensitiveDataFilter())
    logger.setLevel(logging.INFO)
    with caplog.at_level(logging.INFO, logger="test.filter.tuple"):
        logger.info("key=%s", "abcdefghijklmnopqrstuvwxyz123456")
    assert "abcdefgh****" in caplog.text
    assert "abcdefghijklmnopqrstuvwxyz123456" not in caplog.text


def test_sensitive_data_filter_masks_dict_args(caplog):
    logger = logging.getLogger("test.filter.dict")
    logger.addFilter(SensitiveDataFilter())
    logger.setLevel(logging.INFO)
    with caplog.at_level(logging.INFO, logger="test.filter.dict"):
        logger.info("key=%(key)s", {"key": "abcdefghijklmnopqrstuvwxyz123456"})
    assert "abcdefgh****" in caplog.text


def test_log_api_request_logs_info_and_debug_body(capsys):
    setup_logging(log_level="DEBUG")
    log_api_request("https://example.com", "POST", {"a": 1})
    err = capsys.readouterr().err
    assert "POST request to https://example.com" in err
    assert "Request body" in err


def test_log_api_request_without_body_logs_only_info(capsys):
    setup_logging(log_level="INFO")
    log_api_request("https://example.com", "POST", None)
    err = capsys.readouterr().err
    assert "POST request to https://example.com" in err
    assert "Request body" not in err


def test_log_api_response_logs_info_and_debug_body(capsys):
    setup_logging(log_level="DEBUG")
    log_api_response(200, {"ok": True})
    err = capsys.readouterr().err
    assert "Response received: 200" in err
    assert "Response data" in err
