"""
Use-case module contract.

Every use-case module must expose a callable:

    def run_test(device, memory_tool: MemoryTool) -> None: ...

Call validate(module) right after importlib.import_module() to catch
missing or misnamed functions at import time rather than at execution time.
"""
from typing import Callable, Any, TYPE_CHECKING

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
