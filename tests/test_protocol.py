"""Tests for use_cases.protocol — module contract validation + variant detection."""
import types

import pytest

from memory_tool.use_cases.protocol import validate, get_locations


def _module(name="m", **attrs):
    """Build a stand-in module object from keyword attrs."""
    mod = types.SimpleNamespace(__name__=name, **attrs)
    return mod


def test_validate_passes_with_callable_run_test():
    validate(_module(run_test=lambda d, m: None))


def test_validate_fails_when_run_test_missing():
    with pytest.raises(ImportError, match="run_test"):
        validate(_module())


def test_validate_fails_when_run_test_not_callable():
    with pytest.raises(ImportError, match="run_test"):
        validate(_module(run_test=42))


def test_validate_message_includes_module_name():
    with pytest.raises(ImportError, match="my_module"):
        validate(_module(name="my_module"))


def test_get_locations_returns_dict_for_variant_aware():
    locs = {"a": {"label": "A"}, "b": {"label": "B"}}
    assert get_locations(_module(LOCATIONS=locs)) == locs


def test_get_locations_returns_none_when_missing():
    assert get_locations(_module()) is None


def test_get_locations_returns_none_when_empty_dict():
    assert get_locations(_module(LOCATIONS={})) is None


def test_get_locations_returns_none_when_not_dict():
    assert get_locations(_module(LOCATIONS=["a", "b"])) is None
    assert get_locations(_module(LOCATIONS="paris")) is None


def test_get_locations_works_on_real_zoom_module():
    """Sanity check — the production zoom module is variant-aware."""
    from memory_tool.use_cases.sygic_profi import zoom

    locs = get_locations(zoom)
    assert locs is not None
    assert "nepal" in locs
    assert "paris" in locs


def test_get_locations_returns_none_for_real_flat_module():
    """Sanity check — a flat use case (compute) has no LOCATIONS."""
    from memory_tool.use_cases.sygic_profi import compute

    assert get_locations(compute) is None
