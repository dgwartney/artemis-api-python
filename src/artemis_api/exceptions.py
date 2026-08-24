"""Exception hierarchy for the artemis_api package.

All errors raised by :mod:`artemis_api` derive from :class:`ArtemisAPIError`, so
callers that don't care about the specific failure mode can catch a single type.
"""

from __future__ import annotations


class ArtemisAPIError(Exception):
    """Base exception for all artemis_api errors.

    Attributes:
        message: Human-readable description of the error.
        status_code: HTTP status code associated with the error, if any.
    """

    def __init__(self, message: str, status_code: int | None = None) -> None:
        """Initialize the exception.

        Args:
            message: Human-readable description of the error.
            status_code: HTTP status code associated with the error, if any.
        """
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class AuthenticationError(ArtemisAPIError):
    """Raised when the API rejects the configured API key (HTTP 401)."""


class ConfigurationError(ArtemisAPIError):
    """Raised when required configuration (host, app id, API key, ...) is missing or invalid."""


class APIRequestError(ArtemisAPIError):
    """Raised when an API request fails for a reason other than authentication.

    Covers HTTP 404/429/5xx responses as well as network-level failures such as
    DNS resolution errors or connection refusals.
    """


class APIResponseError(ArtemisAPIError):
    """Raised when the API returns a well-formed error response body (HTTP >= 400)."""


class ArtemisTimeoutError(ArtemisAPIError):
    """Raised when a request exceeds the configured timeout."""


class ValidationError(ArtemisAPIError):
    """Raised when client-side input validation fails before any network call is made."""
