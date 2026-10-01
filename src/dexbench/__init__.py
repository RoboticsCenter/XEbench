"""Compatibility imports for the toolkit now named XEbench."""

import sys
from importlib import import_module

from xebench import __version__

__all__ = ["__version__"]

for _name in ("models", "tasks", "recording", "adapters", "policies", "cli"):
    _module = import_module(f"xebench.{_name}")
    sys.modules[f"{__name__}.{_name}"] = _module
    globals()[_name] = _module
