"""Tests for app_info.py — SDK extraction from About-screen UI hierarchy dumps."""
import pytest

from memory_tool.app_info import (
    SDK_PATTERN,
    _extract_text_from_ui_hierarchy,
    _extract_sdk,
)


# ------- SDK_PATTERN regex --------------------------------------------------

def test_sdk_pattern_matches_basic():
    m = SDK_PATTERN.search("SDK 28.4.13")
    assert m is not None
    assert m.group(1) == "28.4.13"


def test_sdk_pattern_case_insensitive():
    assert SDK_PATTERN.search("sdk 25.7.0").group(1) == "25.7.0"
    assert SDK_PATTERN.search("Sdk 35.0.0").group(1) == "35.0.0"


def test_sdk_pattern_finds_in_longer_text():
    text = "Sygic SDK 28.4.13 build 12345 (Apr 2026)"
    assert SDK_PATTERN.search(text).group(1) == "28.4.13"


def test_sdk_pattern_supports_two_or_more_dots():
    # Two-part: 28.4
    assert SDK_PATTERN.search("SDK 28.4").group(1) == "28.4"
    # Four-part: 28.4.13.7
    assert SDK_PATTERN.search("SDK 28.4.13.7").group(1) == "28.4.13.7"


def test_sdk_pattern_no_match_on_unrelated_text():
    assert SDK_PATTERN.search("Version 1.0.0") is None
    assert SDK_PATTERN.search("Build: 12345") is None


def test_sdk_pattern_requires_digits_after_sdk():
    assert SDK_PATTERN.search("SDK release") is None


# ------- _extract_text_from_ui_hierarchy ------------------------------------

def test_extract_text_pulls_text_attributes():
    xml = '<node text="Hello"/><node text="World"/>'
    out = _extract_text_from_ui_hierarchy(xml).split("\n")
    assert "Hello" in out
    assert "World" in out


def test_extract_text_dedupes_case_insensitively():
    xml = '<node text="Hello"/><node text="hello"/><node text="World"/>'
    out = _extract_text_from_ui_hierarchy(xml).split("\n")
    # "hello" was a duplicate of "Hello" (case-insensitive); only one survives.
    lower = [s.lower() for s in out]
    assert lower.count("hello") == 1


def test_extract_text_drops_short_strings():
    xml = '<node text="A"/><node text="OK"/>'
    out = _extract_text_from_ui_hierarchy(xml).split("\n")
    assert "A" not in out
    assert "OK" in out


def test_extract_text_unescapes_html_entities():
    xml = '<node text="A&amp;B"/>'
    assert "A&B" in _extract_text_from_ui_hierarchy(xml).split("\n")


def test_extract_text_returns_empty_on_blank_input():
    assert _extract_text_from_ui_hierarchy("") == ""
    assert _extract_text_from_ui_hierarchy(None) == ""


def test_extract_text_strips_whitespace():
    xml = '<node text="  Hello  "/>'
    assert "Hello" in _extract_text_from_ui_hierarchy(xml).split("\n")


# ------- _extract_sdk -------------------------------------------------------

def test_extract_sdk_via_callback():
    def fake_read_about(_device):
        return {"ui_hierarchy": '<n text="Sygic SDK 28.4.13 build 1"/>'}
    assert _extract_sdk(device=None, read_about=fake_read_about) == "28.4.13"


def test_extract_sdk_returns_none_when_no_callback():
    assert _extract_sdk(device=None, read_about=None) is None


def test_extract_sdk_returns_none_when_no_match():
    fake = lambda _d: {"ui_hierarchy": '<n text="just some text"/>'}
    assert _extract_sdk(device=None, read_about=fake) is None


def test_extract_sdk_returns_none_when_callback_raises():
    def boom(_d):
        raise RuntimeError("device disconnected")
    assert _extract_sdk(device=None, read_about=boom) is None


def test_extract_sdk_returns_none_when_callback_returns_non_dict():
    fake = lambda _d: "not a dict"
    assert _extract_sdk(device=None, read_about=fake) is None


def test_extract_sdk_returns_none_when_hierarchy_missing():
    fake = lambda _d: {}  # no ui_hierarchy key
    assert _extract_sdk(device=None, read_about=fake) is None
