"""Tests for artemis_api.config."""

import pytest

from artemis_api.config import Config
from artemis_api.exceptions import ConfigurationError
from artemis_api.profiles import ProfileManager


def test_default_host_and_env_name(profile_manager):
    config = Config(app_id="aa-1", api_key="kg-1", profile_manager=profile_manager)
    assert config.host == "https://agents.kore.ai"
    assert config.env_name == "production"
    assert config.timeout == 30.0


def test_explicit_kwargs_take_precedence_over_env(monkeypatch, profile_manager):
    monkeypatch.setenv("ARTEMIS_HOST", "https://env.example.com")
    config = Config(
        host="https://kwarg.example.com",
        app_id="aa-1",
        api_key="kg-1",
        profile_manager=profile_manager,
    )
    assert config.host == "https://kwarg.example.com"


def test_env_var_takes_precedence_over_profile(monkeypatch, profile_manager):
    profile_manager.add_profile("p", host="https://profile.example.com", app_id="aa-p")
    monkeypatch.setenv("ARTEMIS_HOST", "https://env.example.com")
    config = Config(profile="p", api_key="kg-1", profile_manager=profile_manager)
    assert config.host == "https://env.example.com"


def test_profile_value_used_when_no_kwarg_or_env(monkeypatch, profile_manager):
    monkeypatch.delenv("ARTEMIS_HOST", raising=False)
    profile_manager.add_profile(
        "p", host="https://profile.example.com", app_id="aa-p", api_key="kg-p"
    )
    config = Config(profile="p", profile_manager=profile_manager)
    assert config.host == "https://profile.example.com"
    assert config.app_id == "aa-p"
    assert config.api_key == "kg-p"


def test_default_used_when_nothing_else_set(monkeypatch, profile_manager):
    monkeypatch.delenv("ARTEMIS_HOST", raising=False)
    config = Config(app_id="aa-1", api_key="kg-1", profile_manager=profile_manager)
    assert config.host == "https://agents.kore.ai"


def test_all_env_vars_are_honored(monkeypatch, profile_manager):
    monkeypatch.setenv("ARTEMIS_HOST", "https://env.example.com")
    monkeypatch.setenv("ARTEMIS_APP_ID", "aa-env")
    monkeypatch.setenv("ARTEMIS_ENV_NAME", "staging")
    monkeypatch.setenv("ARTEMIS_API_KEY", "kg-env")
    monkeypatch.setenv("ARTEMIS_USER_REFERENCE", "u-env")
    monkeypatch.setenv("ARTEMIS_TIMEOUT", "12")
    config = Config(profile_manager=profile_manager)
    assert config.host == "https://env.example.com"
    assert config.app_id == "aa-env"
    assert config.env_name == "staging"
    assert config.api_key == "kg-env"
    assert config.user_reference == "u-env"
    assert config.timeout == 12.0


def test_user_reference_falls_back_to_generated_uuid(monkeypatch, profile_manager):
    monkeypatch.delenv("ARTEMIS_USER_REFERENCE", raising=False)
    config = Config(app_id="aa-1", api_key="kg-1", profile_manager=profile_manager)
    assert config.user_reference.startswith("repl-")
    assert len(config.user_reference) == len("repl-") + 8


def test_app_id_property_raises_when_missing(profile_manager):
    config = Config(api_key="kg-1", profile_manager=profile_manager)
    with pytest.raises(ConfigurationError):
        _ = config.app_id


def test_api_key_property_raises_when_missing(profile_manager):
    config = Config(app_id="aa-1", profile_manager=profile_manager)
    with pytest.raises(ConfigurationError):
        _ = config.api_key


def test_validate_raises_when_app_id_missing(profile_manager):
    config = Config(api_key="kg-1", profile_manager=profile_manager)
    with pytest.raises(ConfigurationError):
        config.validate()


def test_validate_raises_when_api_key_missing(profile_manager):
    config = Config(app_id="aa-1", profile_manager=profile_manager)
    with pytest.raises(ConfigurationError):
        config.validate()


def test_validate_passes_when_required_fields_present(profile_manager):
    config = Config(app_id="aa-1", api_key="kg-1", profile_manager=profile_manager)
    config.validate()  # should not raise


def test_repr_masks_api_key(profile_manager):
    config = Config(app_id="aa-1", api_key="kg-1234567890", profile_manager=profile_manager)
    text = repr(config)
    assert "kg-1234567890" not in text
    assert "kg-12345" in text


def test_repr_handles_missing_api_key(profile_manager):
    config = Config(app_id="aa-1", profile_manager=profile_manager)
    text = repr(config)
    assert "not set" in text


def test_unknown_profile_raises_configuration_error(tmp_path):
    manager = ProfileManager(path=tmp_path / "profiles.json")
    with pytest.raises(ConfigurationError):
        Config(profile="missing", profile_manager=manager)


def test_default_profile_manager_used_when_not_injected(monkeypatch, tmp_path):
    fallback = ProfileManager(path=tmp_path / "p.json")
    monkeypatch.setattr("artemis_api.config.ProfileManager", lambda: fallback)
    config = Config(app_id="aa-1", api_key="kg-1")
    assert config.app_id == "aa-1"
