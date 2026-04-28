"""
    pint
    ~~~~

    Pint is Python module/package to define, operate and manipulate
    **physical quantities**: the product of a numerical value and a
    unit of measurement. It allows arithmetic operations between them
    and conversions from and to different units.
"""
from __future__ import annotations

from .errors import (
    DefinitionSyntaxError,
    DimensionalityError,
    LogarithmicUnitCalculusError,
    OffsetUnitCalculusError,
    PintError,
    RedefinitionError,
    UndefinedUnitError,
    UnitStrippedWarning,
)
from .formatting import register_unit_format
from .registry import LazyRegistry, UnitRegistry
from .util import logger

# Application registry support
from ._application_registry import (
    ApplicationRegistry,
    get_application_registry,
    set_application_registry,
)

# Create application registry
application_registry: ApplicationRegistry = ApplicationRegistry(LazyRegistry())


def _unpickle_quantity(cls, *args):
    """Used to unpickle quantities."""
    from .facets.plain import PlainQuantity

    ureg = get_application_registry()
    return ureg.Quantity.__class__.__new__(ureg.Quantity.__class__, *args)


def _unpickle_unit(cls, *args):
    """Used to unpickle units."""
    ureg = get_application_registry()
    return ureg.Unit.__class__.__new__(ureg.Unit.__class__, *args)


def _unpickle_measurement(cls, *args):
    """Used to unpickle measurements."""
    ureg = get_application_registry()
    return ureg.Measurement.__class__.__new__(ureg.Measurement.__class__, *args)


# Make Quantity, Unit, Measurement available at package level via proxy
class _Proxy:
    def __init__(self, attr_name):
        self._attr_name = attr_name

    def __call__(self, *args, **kwargs):
        return getattr(get_application_registry(), self._attr_name)(*args, **kwargs)

    def __getattr__(self, item):
        return getattr(getattr(get_application_registry(), self._attr_name), item)

    def __repr__(self):
        return f"<{self._attr_name} proxy>"


Quantity = _Proxy("Quantity")
Unit = _Proxy("Unit")
Measurement = _Proxy("Measurement")
Context = _Proxy("Context")


# pi_theorem function
from . import pi_theorem as _pi_theorem

pi_theorem = _pi_theorem.pi_theorem


def __getattr__(name):
    if name in ("Quantity", "Unit", "Measurement", "Context"):
        return getattr(get_application_registry(), name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "ApplicationRegistry",
    "Context",
    "DefinitionSyntaxError",
    "DimensionalityError",
    "LogarithmicUnitCalculusError",
    "Measurement",
    "OffsetUnitCalculusError",
    "PintError",
    "Quantity",
    "RedefinitionError",
    "UndefinedUnitError",
    "Unit",
    "UnitRegistry",
    "UnitStrippedWarning",
    "get_application_registry",
    "logger",
    "pi_theorem",
    "register_unit_format",
    "set_application_registry",
]

try:
    from importlib.metadata import version
except ImportError:
    from importlib_metadata import version  # type: ignore

try:
    __version__ = version("pint")
except Exception:
    __version__ = "0.0.0.dev0"
