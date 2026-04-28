"""
    pint._application_registry
    ~~~~~~~~~~~~~~~~~~~~~~~~~~

    Application registry support.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .registry import UnitRegistry


class ApplicationRegistry:
    """A wrapper around a UnitRegistry that can be replaced at runtime.

    This class provides a stable reference that can be updated to point
    to different UnitRegistry instances.
    """

    def __init__(self, registry: "UnitRegistry"):
        object.__setattr__(self, "_registry", registry)

    def get(self) -> "UnitRegistry":
        """Get the underlying registry."""
        return self._registry

    def set(self, registry: "UnitRegistry") -> None:
        """Set the underlying registry."""
        object.__setattr__(self, "_registry", registry)

    def __getattr__(self, name: str) -> Any:
        registry = object.__getattribute__(self, "_registry")
        # Force initialization for lazy registries
        if hasattr(registry, "_ensure_initialized"):
            registry._ensure_initialized()
        return getattr(registry, name)

    def __setattr__(self, name: str, value: Any) -> None:
        registry = object.__getattribute__(self, "_registry")
        setattr(registry, name, value)

    def __call__(self, *args, **kwargs):
        registry = object.__getattribute__(self, "_registry")
        if hasattr(registry, "_ensure_initialized"):
            registry._ensure_initialized()
        return registry(*args, **kwargs)


def get_application_registry() -> ApplicationRegistry:
    """Get the global application registry.

    Returns
    -------
    ApplicationRegistry
        The global application registry wrapper.
    """
    from . import application_registry

    return application_registry


def set_application_registry(registry: "UnitRegistry") -> None:
    """Set the global application registry.

    Parameters
    ----------
    registry : UnitRegistry
        The registry to use as the global application registry.
    """
    from . import application_registry

    application_registry.set(registry)
