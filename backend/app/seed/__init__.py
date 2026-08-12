from importlib import import_module
from typing import Any

__all__ = [
    "DRIVERS",
    "MVP_CALENDAR",
    "TEAMS",
    "TRACKS",
    "SeedSummary",
    "seed_mvp_catalog",
    "seed_mvp_catalog_database",
]


def __getattr__(name: str) -> Any:
    if name in __all__:
        return getattr(import_module("app.seed.mvp"), name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
