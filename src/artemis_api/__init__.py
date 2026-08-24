"""artemis_api: a REPL chat client and library for the Kore.ai Agent Platform (Artemis) API.

The public surface re-exported here is safe to use standalone, without the
CLI or REPL: :class:`Config` and :class:`ArtemisClient` can be used directly
from any Python script.
"""

from artemis_api import api_reference
from artemis_api.api_reference import SessionInfo
from artemis_api.client import ArtemisClient
from artemis_api.config import Config
from artemis_api.exceptions import (
    APIRequestError,
    APIResponseError,
    ArtemisAPIError,
    ArtemisTimeoutError,
    AuthenticationError,
    ConfigurationError,
    ValidationError,
)
from artemis_api.profiles import ProfileManager

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "api_reference",
    "ArtemisAPIError",
    "ArtemisClient",
    "ArtemisTimeoutError",
    "APIRequestError",
    "APIResponseError",
    "AuthenticationError",
    "Config",
    "ConfigurationError",
    "ProfileManager",
    "SessionInfo",
    "ValidationError",
]
