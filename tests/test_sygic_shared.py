"""Tests for the shared Sygic Profi UI helpers."""
from memory_tool.use_cases.sygic_profi import shared


class FakeSelector:
    """Small stand-in for a uiautomator selector."""

    def __init__(self, exists_sequence=None, info=None):
        self.exists_sequence = list(exists_sequence or [False])
        self.info = info or {}
        self.click_calls = 0

    def exists(self, timeout=0):
        if self.exists_sequence:
            return self.exists_sequence.pop(0)
        return False

    def click(self):
        self.click_calls += 1


class FakeDevice:
    """Minimal fake device that supports selector lookups and basic actions."""

    def __init__(self, selectors=None, info=None):
        self.selectors = selectors or {}
        self.info = info or {"displayWidth": 1080, "displayHeight": 2400}
        self.clicks = []
        self.back_presses = 0

    def __call__(self, **selector):
        return self.selectors.setdefault(tuple(sorted(selector.items())), FakeSelector())

    def click(self, x, y):
        self.clicks.append((x, y))

    def press(self, key):
        if key == "back":
            self.back_presses += 1

    def dump_hierarchy(self, compressed=False):
        return "<hierarchy/>"


def _selector_key(resource_id):
    return (("resourceId", resource_id),)


def test_wait_for_map_ready_accepts_menu_icon_without_search_bar():
    device = FakeDevice(
        selectors={
            _selector_key(shared.SEARCH_BAR_ID): FakeSelector([False]),
            _selector_key(shared.MENU_ICON_ID): FakeSelector([True]),
        }
    )

    assert shared.wait_for_map_ready(device, timeout=1) is True


def test_tap_search_bar_uses_existing_search_field():
    field = FakeSelector([True])
    device = FakeDevice(selectors={_selector_key(shared.SEARCH_FIELD_ID): field})

    shared.tap_search_bar(device)

    assert field.click_calls == 1
    assert device.clicks == []


def test_tap_search_bar_falls_back_to_top_bar_click_when_input_missing():
    menu_icon = FakeSelector(
        [True],
        info={"bounds": {"left": 20, "top": 100, "right": 120, "bottom": 200}},
    )
    search_field = FakeSelector([False, True])
    device = FakeDevice(
        selectors={
            _selector_key(shared.SEARCH_FIELD_ID): search_field,
            _selector_key(shared.SEARCH_BAR_ID): FakeSelector([False, False]),
            _selector_key(shared.MENU_ICON_ID): FakeSelector(
                [True, True],
                info=menu_icon.info,
            ),
            _selector_key(shared.PROFILE_ICON_ID): FakeSelector([False]),
        }
    )

    shared.tap_search_bar(device)

    assert device.clicks == [(540, 150)]
    assert search_field.click_calls == 1


def test_tap_search_bar_raises_and_dumps_when_map_ready_but_search_stays_missing(
    monkeypatch,
):
    dumped = []
    monkeypatch.setattr(shared, "dump_hierarchy", lambda device, name: dumped.append(name))
    device = FakeDevice(
        selectors={
            _selector_key(shared.SEARCH_FIELD_ID): FakeSelector([False, False]),
            _selector_key(shared.SEARCH_BAR_ID): FakeSelector([False, False]),
            _selector_key(shared.MENU_ICON_ID): FakeSelector([True, True, True]),
            _selector_key(shared.PROFILE_ICON_ID): FakeSelector([False]),
        }
    )

    try:
        shared.tap_search_bar(device)
    except RuntimeError as exc:
        assert "sygic_search_bar_missing" in str(exc)
    else:
        raise AssertionError("tap_search_bar() should have raised RuntimeError")

    assert dumped == ["sygic_search_bar_missing"]
