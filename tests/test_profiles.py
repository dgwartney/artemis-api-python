"""Tests for artemis_api.profiles."""

import os
import stat

import pytest

from artemis_api.exceptions import ConfigurationError
from artemis_api.profiles import ProfileManager, mask_api_key


def test_mask_api_key_masks_long_key():
    assert mask_api_key("abcdefghijklmnop") == "abcdefgh****"


def test_mask_api_key_handles_none():
    assert mask_api_key(None) == "<not set>"


def test_mask_api_key_handles_empty_string():
    assert mask_api_key("") == "<not set>"


def test_list_profiles_empty_when_no_file(profile_manager):
    assert profile_manager.list_profiles() == {}


def test_add_and_get_profile(profile_manager):
    profile_manager.add_profile("work", app_id="aa-1", api_key="kg-1")
    profile = profile_manager.get_profile("work")
    assert profile == {"app_id": "aa-1", "api_key": "kg-1"}


def test_add_profile_ignores_unknown_fields(profile_manager):
    profile_manager.add_profile("work", app_id="aa-1", bogus="ignored")
    profile = profile_manager.get_profile("work")
    assert "bogus" not in profile


def test_add_profile_overwrites_existing(profile_manager):
    profile_manager.add_profile("work", app_id="aa-1")
    profile_manager.add_profile("work", app_id="aa-2")
    assert profile_manager.get_profile("work")["app_id"] == "aa-2"


def test_get_profile_raises_for_unknown_name(profile_manager):
    with pytest.raises(ConfigurationError):
        profile_manager.get_profile("missing")


def test_delete_profile(profile_manager):
    profile_manager.add_profile("work", app_id="aa-1")
    profile_manager.delete_profile("work")
    assert profile_manager.list_profiles() == {}


def test_delete_profile_raises_for_unknown_name(profile_manager):
    with pytest.raises(ConfigurationError):
        profile_manager.delete_profile("missing")


def test_delete_default_profile_clears_default(profile_manager):
    profile_manager.add_profile("work", app_id="aa-1")
    profile_manager.set_default("work")
    profile_manager.delete_profile("work")
    assert profile_manager.get_default_profile_name() is None


def test_set_default_and_get_default(profile_manager):
    profile_manager.add_profile("work", app_id="aa-1")
    profile_manager.set_default("work")
    assert profile_manager.get_default_profile_name() == "work"


def test_set_default_raises_for_unknown_name(profile_manager):
    with pytest.raises(ConfigurationError):
        profile_manager.set_default("missing")


def test_get_default_profile_name_none_when_unset(profile_manager):
    assert profile_manager.get_default_profile_name() is None


def test_file_and_dir_permissions(profile_manager, profiles_path):
    profile_manager.add_profile("work", app_id="aa-1")
    dir_mode = stat.S_IMODE(os.stat(profiles_path.parent).st_mode)
    file_mode = stat.S_IMODE(os.stat(profiles_path).st_mode)
    assert dir_mode == 0o700
    assert file_mode == 0o600


def test_corrupt_profiles_file_treated_as_empty(profiles_path):
    profiles_path.parent.mkdir(parents=True, exist_ok=True)
    profiles_path.write_text("not valid json{")
    manager = ProfileManager(path=profiles_path)
    assert manager.list_profiles() == {}
    assert manager.get_default_profile_name() is None


def test_save_cleans_up_temp_file_on_failure(profile_manager, profiles_path, monkeypatch):
    def failing_dump(*args, **kwargs):
        raise ValueError("boom")

    monkeypatch.setattr("json.dump", failing_dump)
    with pytest.raises(ValueError):
        profile_manager.add_profile("work", app_id="aa-1")
    leftover_temp_files = list(profiles_path.parent.glob(".profiles-*.tmp"))
    assert leftover_temp_files == []


def test_round_trip_multiple_profiles(profile_manager):
    profile_manager.add_profile("a", app_id="aa-a")
    profile_manager.add_profile("b", app_id="aa-b")
    profiles = profile_manager.list_profiles()
    assert set(profiles) == {"a", "b"}
