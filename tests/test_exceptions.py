"""Tests for artemis_api.exceptions."""

from artemis_api.exceptions import (
    APIRequestError,
    APIResponseError,
    ArtemisAPIError,
    ArtemisTimeoutError,
    AuthenticationError,
    ConfigurationError,
    ValidationError,
)


def test_base_exception_stores_message_and_status_code():
    exc = ArtemisAPIError("boom", status_code=500)
    assert exc.message == "boom"
    assert exc.status_code == 500
    assert str(exc) == "boom"


def test_base_exception_status_code_defaults_to_none():
    exc = ArtemisAPIError("boom")
    assert exc.status_code is None


def test_all_subclasses_derive_from_base():
    for cls in (
        AuthenticationError,
        ConfigurationError,
        APIRequestError,
        APIResponseError,
        ArtemisTimeoutError,
        ValidationError,
    ):
        assert issubclass(cls, ArtemisAPIError)
        instance = cls("message")
        assert instance.message == "message"
