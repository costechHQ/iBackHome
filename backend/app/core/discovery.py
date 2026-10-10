"""Finds every feature and base module automatically.

This is what lets five people add code without ever editing a shared file:
drop a `router.py`, `models.py` or `tasks.py` into your own folder and it is picked up.
"""

import importlib
import importlib.util
import pkgutil
from collections.abc import Iterator
from types import ModuleType

import app.base
import app.features

PACKAGES = (app.base, app.features)


def module_names(filename: str) -> Iterator[str]:
    """Yield e.g. 'app.features.milestones.router' for every package that has that file."""
    for parent in PACKAGES:
        for info in sorted(pkgutil.iter_modules(parent.__path__), key=lambda m: m.name):
            if not info.ispkg:
                continue
            name = f"{parent.__name__}.{info.name}.{filename}"
            if importlib.util.find_spec(name) is not None:
                yield name


def import_all(filename: str) -> list[ModuleType]:
    return [importlib.import_module(name) for name in module_names(filename)]
