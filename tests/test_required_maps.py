"""Tests for runner.required_maps_for — which offline maps a use case needs."""
import types

from memory_tool.runner import required_maps_for


def _module(**attrs):
    return types.SimpleNamespace(__name__="m", **attrs)


def test_flat_module_uses_required_maps():
    assert required_maps_for(_module(REQUIRED_MAPS=["sk", "at"])) == ["sk", "at"]


def test_module_without_maps_needs_none():
    assert required_maps_for(_module()) == []


def test_variant_module_uses_location_maps():
    mod = _module(LOCATIONS={"a": {"required_maps": ["np"]}, "b": {"required_maps": ["fr"]}})
    assert required_maps_for(mod, "b") == ["fr"]


def test_variant_module_falls_back_to_default_location():
    mod = _module(LOCATIONS={"a": {"required_maps": ["np"]}}, DEFAULT_LOCATION="a")
    assert required_maps_for(mod) == ["np"]


def test_real_use_cases_declare_maps():
    from memory_tool.use_cases.sygic_profi import compute, zoom

    assert required_maps_for(compute) == ["sk", "at"]
    assert required_maps_for(zoom, "paris") == ["fr"]
