"""Configuration resolution for artemis_api.

:class:`Config` resolves connection settings from, in order of precedence:
an explicit constructor keyword argument, an ``ARTEMIS_*`` environment
variable, a named profile (see :mod:`artemis_api.profiles`), and finally a
built-in default. The same class is used by the CLI and by library callers.
"""

from __future__ import annotations

import os
import uuid
from typing import Any

from artemis_api.exceptions import ConfigurationError
from artemis_api.profiles import ProfileManager

_DEFAULT_HOST = "https://agents.kore.ai"
_DEFAULT_ENV_NAME = "production"
_DEFAULT_TIMEOUT = 30.0


class Config:
    """Resolves and holds connection configuration for :class:`~artemis_api.client.ArtemisClient`.

    Attributes:
        host: Base host for the Agent Platform environment.
        app_id: The Agentic App's ID.
        env_name: The deployment environment name.
        api_key: The scoped API key.
        user_reference: A stable identifier for this client/user.
        timeout: Request timeout, in seconds.
    """

    def __init__(
        self,
        profile: str | None = None,
        host: str | None = None,
        app_id: str | None = None,
        env_name: str | None = None,
        api_key: str | None = None,
        user_reference: str | None = None,
        timeout: float | None = None,
        *,
        profile_manager: ProfileManager | None = None,
    ) -> None:
        """Resolve configuration from kwargs, environment variables, and an optional profile.

        Args:
            profile: Name of a saved profile to fall back to. Ignored if ``None``.
            host: Explicit host override.
            app_id: Explicit app ID override.
            env_name: Explicit environment name override.
            api_key: Explicit API key override.
            user_reference: Explicit user reference override.
            timeout: Explicit timeout override, in seconds.
            profile_manager: Injectable :class:`~artemis_api.profiles.ProfileManager`,
                primarily for testing. Defaults to a new instance.

        Raises:
            ConfigurationError: If ``profile`` is given but no such profile exists.
        """
        manager = profile_manager or ProfileManager()
        profile_values: dict[str, Any] = manager.get_profile(profile) if profile else {}

        self._host = self._resolve(host, "ARTEMIS_HOST", profile_values.get("host"), _DEFAULT_HOST)
        self._app_id = self._resolve(app_id, "ARTEMIS_APP_ID", profile_values.get("app_id"), None)
        self._env_name = self._resolve(
            env_name, "ARTEMIS_ENV_NAME", profile_values.get("env_name"), _DEFAULT_ENV_NAME
        )
        self._api_key = self._resolve(
            api_key, "ARTEMIS_API_KEY", profile_values.get("api_key"), None
        )
        self._user_reference = self._resolve(
            user_reference,
            "ARTEMIS_USER_REFERENCE",
            profile_values.get("user_reference"),
            None,
        )

        resolved_timeout = self._resolve(
            timeout, "ARTEMIS_TIMEOUT", profile_values.get("timeout"), _DEFAULT_TIMEOUT
        )
        self._timeout = float(resolved_timeout)

        if self._user_reference is None:
            self._user_reference = f"repl-{uuid.uuid4().hex[:8]}"

    @staticmethod
    def _resolve(
        explicit: Any, env_var: str, profile_value: Any, default: Any
    ) -> Any:
        """Resolve a single field's value by precedence.

        Args:
            explicit: The explicitly-passed constructor value, or ``None``.
            env_var: The environment variable name to check next.
            profile_value: The value found in the loaded profile, or ``None``.
            default: The built-in default value.

        Returns:
            The first non-``None`` value found, in precedence order, or ``default``.
        """
        if explicit is not None:
            return explicit
        env_value = os.environ.get(env_var)
        if env_value:
            return env_value
        if profile_value is not None:
            return profile_value
        return default

    @property
    def host(self) -> str:
        """The base host for the Agent Platform environment."""
        return self._host

    @property
    def app_id(self) -> str:
        """The Agentic App's ID.

        Raises:
            ConfigurationError: If no app ID was configured.
        """
        if not self._app_id:
            raise ConfigurationError(
                "App ID not configured. Set ARTEMIS_APP_ID, use --app-id, or select a profile."
            )
        return self._app_id

    @property
    def env_name(self) -> str:
        """The deployment environment name."""
        return self._env_name

    @property
    def api_key(self) -> str:
        """The scoped API key.

        Raises:
            ConfigurationError: If no API key was configured.
        """
        if not self._api_key:
            raise ConfigurationError(
                "API key not configured. Set ARTEMIS_API_KEY, use --api-key, or select a profile."
            )
        return self._api_key

    @property
    def user_reference(self) -> str:
        """A stable identifier for this client/user."""
        return self._user_reference

    @property
    def timeout(self) -> float:
        """Request timeout, in seconds."""
        return self._timeout

    def validate(self) -> None:
        """Validate that all required configuration is present.

        Raises:
            ConfigurationError: If ``app_id`` or ``api_key`` is missing.
        """
        _ = self.app_id
        _ = self.api_key

    def __repr__(self) -> str:
        """Return a string representation with the API key masked."""
        from artemis_api.profiles import mask_api_key

        return (
            f"Config(host={self._host!r}, app_id={self._app_id!r}, "
            f"env_name={self._env_name!r}, api_key={mask_api_key(self._api_key)!r}, "
            f"user_reference={self._user_reference!r}, timeout={self._timeout!r})"
        )
