"""
Use-case module contract.

Every use-case module must expose a callable:

    def run_test(device, memory_tool: MemoryTool, location: str | None = None) -> None: ...

The `location` keyword is only used by variant-aware modules (those that expose
a LOCATIONS dict). Flat modules can ignore it.

Call validate(module) right after importlib.import_module() to catch
missing or misnamed functions at import time rather than at execution time.
"""
from typing import Callable, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from memory_tool.memory_monitor import MemoryTool

RunTestFn = Callable[[Any, "MemoryTool"], None]


def validate(module) -> None:
    """Raise ImportError if the module does not expose a callable run_test."""
    if not callable(getattr(module, "run_test", None)):
        raise ImportError(
            f"Use-case module '{module.__name__}' must define "
            f"a callable run_test(device, memory_tool)"
        )


def get_locations(module) -> Optional[dict]:
    """
    Return the LOCATIONS dict if the module is variant-aware, else None.

    A variant-aware module exposes LOCATIONS — a dict mapping variant keys
    (e.g. "paris") to a per-variant config dict. run_test must accept a
    `location` keyword argument.
    """
    locations = getattr(module, "LOCATIONS", None)
    if isinstance(locations, dict) and locations:
        return locations
    return None
