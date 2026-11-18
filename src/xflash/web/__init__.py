"""Web application and local dashboard for Laptop Buyer Kit."""
from __future__ import annotations

from typing import Any


def run_server(*args: Any, **kwargs: Any) -> Any:
    from .server import run_server as _run_server
    return _run_server(*args, **kwargs)


def create_server(*args: Any, **kwargs: Any) -> Any:
    from .server import create_server as _create_server
    return _create_server(*args, **kwargs)


__all__ = ["run_server", "create_server"]
