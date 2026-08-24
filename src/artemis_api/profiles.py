"""Named profile storage for talking to multiple Artemis agents.

Profiles let a user save a (host, app_id, env_name, api_key, user_reference,
timeout) tuple under a short name and select it later with ``--profile
NAME`` instead of repeating flags/env vars for every agent they talk to.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from artemis_api.exceptions import ConfigurationError

_PROFILE_FIELDS = ("host", "app_id", "env_name", "api_key", "user_reference", "timeout")


def _default_profiles_path() -> Path:
    """Return the default path to the profiles store.

    Returns:
        ``~/.artemis/profiles.json``, expanded for the current user.
    """
    return Path.home() / ".artemis" / "profiles.json"


def mask_api_key(api_key: str | None) -> str:
    """Mask an API key for display, keeping only a short, non-sensitive prefix.

    Args:
        api_key: The raw API key, or ``None``.

    Returns:
        A masked string such as ``"abcdefgh****"``, or ``"<not set>"`` if
        ``api_key`` is falsy.

    Examples:
        >>> mask_api_key("abcdefghijklmnop")
        'abcdefgh****'
    """
    if not api_key:
        return "<not set>"
    return f"{api_key[:8]}****"


class ProfileManager:
    """Manages named connection profiles stored as JSON on disk.

    The profile store is created with restrictive permissions (``0700`` on
    the containing directory, ``0600`` on the file) and written atomically
    (write to a temp file in the same directory, then ``os.replace``) so a
    crash mid-write never corrupts existing profiles.
    """

    def __init__(self, path: Path | None = None) -> None:
        """Initialize the manager.

        Args:
            path: Path to the profiles JSON file. Defaults to
                ``~/.artemis/profiles.json``.
        """
        self._path = path or _default_profiles_path()

    def _load(self) -> dict[str, Any]:
        """Load the profile store from disk.

        Returns:
            The parsed store, or an empty default structure if the file
            doesn't exist or is corrupt.
        """
        if not self._path.exists():
            return {"profiles": {}, "default_profile": None}

        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {"profiles": {}, "default_profile": None}

        data.setdefault("profiles", {})
        data.setdefault("default_profile", None)
        return data

    def _save(self, data: dict[str, Any]) -> None:
        """Atomically write the profile store to disk with restrictive permissions.

        Args:
            data: The full store structure to persist.
        """
        self._path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)

        fd, tmp_name = tempfile.mkstemp(dir=self._path.parent, prefix=".profiles-", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(data, handle, indent=2)
            os.chmod(tmp_name, 0o600)
            os.replace(tmp_name, self._path)
        except BaseException:
            Path(tmp_name).unlink(missing_ok=True)
            raise

    def list_profiles(self) -> dict[str, dict[str, Any]]:
        """List all stored profiles.

        Returns:
            A mapping of profile name to its stored fields (API keys are
            **not** masked here -- use :func:`mask_api_key` when displaying).
        """
        return self._load()["profiles"]

    def get_profile(self, name: str) -> dict[str, Any]:
        """Get a single profile's raw stored fields.

        Args:
            name: The profile name.

        Returns:
            The profile's stored fields.

        Raises:
            ConfigurationError: If no profile with that name exists.
        """
        profiles = self.list_profiles()
        if name not in profiles:
            raise ConfigurationError(f"No profile named {name!r} exists.")
        return profiles[name]

    def add_profile(self, name: str, **fields: Any) -> None:
        """Create or overwrite a profile.

        Args:
            name: The profile name.
            **fields: Any of ``host``, ``app_id``, ``env_name``, ``api_key``,
                ``user_reference``, ``timeout``. Unrecognized keys are ignored.
        """
        data = self._load()
        stored = {key: value for key, value in fields.items() if key in _PROFILE_FIELDS}
        data["profiles"][name] = stored
        self._save(data)

    def delete_profile(self, name: str) -> None:
        """Delete a profile.

        Args:
            name: The profile name to delete.

        Raises:
            ConfigurationError: If no profile with that name exists.
        """
        data = self._load()
        if name not in data["profiles"]:
            raise ConfigurationError(f"No profile named {name!r} exists.")
        del data["profiles"][name]
        if data.get("default_profile") == name:
            data["default_profile"] = None
        self._save(data)

    def set_default(self, name: str) -> None:
        """Set the default profile.

        Args:
            name: The profile name to mark as default.

        Raises:
            ConfigurationError: If no profile with that name exists.
        """
        data = self._load()
        if name not in data["profiles"]:
            raise ConfigurationError(f"No profile named {name!r} exists.")
        data["default_profile"] = name
        self._save(data)

    def get_default_profile_name(self) -> str | None:
        """Get the name of the default profile, if one is set.

        Returns:
            The default profile's name, or ``None`` if none is set.
        """
        return self._load()["default_profile"]
