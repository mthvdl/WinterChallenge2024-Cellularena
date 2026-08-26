"""Small helpers for dynamically loading factories from module paths."""
from __future__ import annotations

import importlib
from typing import Any


def load_symbol(path: str) -> Any:
    """Load ``module:attr`` and return the resolved attribute."""
    if ":" not in path:
        raise ValueError(f"Invalid symbol path '{path}'. Expected format: module:attr")
    module_name, attr_name = path.split(":", 1)
    module = importlib.import_module(module_name)
    if not hasattr(module, attr_name):
        raise AttributeError(f"Module '{module_name}' has no attribute '{attr_name}'.")
    return getattr(module, attr_name)