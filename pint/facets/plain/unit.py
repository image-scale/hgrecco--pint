"""
    pint.facets.plain.unit
    ~~~~~~~~~~~~~~~~~~~~~~

    Unit class for the plain facet.
"""
from __future__ import annotations

import copy
import operator
from numbers import Number
from typing import TYPE_CHECKING, Any, Optional, Union

from ...util import UnitsContainer

if TYPE_CHECKING:
    from .registry import PlainRegistry


# Re-export UnitsContainer for backwards compatibility
__all__ = ["PlainUnit", "UnitsContainer"]


class PlainUnit:
    """A unit of measurement.

    This class should not be instantiated directly. Use the UnitRegistry
    instead.
    """

    __slots__ = ("_units", "_REGISTRY")

    def __init__(
        self,
        units: Union[UnitsContainer, str, "PlainUnit", None] = None,
        registry: Optional["PlainRegistry"] = None,
    ):
        if registry is None:
            from ... import get_application_registry

            registry = get_application_registry()

        self._REGISTRY = registry

        if units is None:
            self._units = UnitsContainer()
        elif isinstance(units, UnitsContainer):
            self._units = units
        elif isinstance(units, PlainUnit):
            self._units = units._units
        elif isinstance(units, str):
            self._units = registry.parse_units(units)._units
        else:
            raise TypeError(
                f"units must be a string, UnitsContainer, or Unit, not {type(units)}"
            )

    def __copy__(self):
        return self.__class__(self._units, self._REGISTRY)

    def __deepcopy__(self, memo):
        return self.__class__(copy.deepcopy(self._units, memo), self._REGISTRY)

    def __str__(self):
        return self._REGISTRY.formatter.format_unit(self)

    def __repr__(self):
        return f'Unit("{self}")'

    def __format__(self, spec):
        return self._REGISTRY.formatter.format_unit(self, spec)

    def __hash__(self):
        return hash(self._units)

    def __eq__(self, other):
        if isinstance(other, PlainUnit):
            return self._units == other._units
        if isinstance(other, str):
            return self == self._REGISTRY.parse_units(other)
        return NotImplemented

    def __ne__(self, other):
        result = self.__eq__(other)
        if result is NotImplemented:
            return result
        return not result

    def __mul__(self, other):
        if isinstance(other, Number):
            return self._REGISTRY.Quantity(other, self)
        if isinstance(other, PlainUnit):
            return self.__class__(self._units * other._units, self._REGISTRY)
        if hasattr(other, "_units"):
            return self._REGISTRY.Quantity(
                other.magnitude, self._units * other._units
            )
        # Try to let the other operand handle it
        return NotImplemented

    def __rmul__(self, other):
        if isinstance(other, Number):
            return self._REGISTRY.Quantity(other, self)
        return NotImplemented

    def __truediv__(self, other):
        if isinstance(other, Number):
            return self._REGISTRY.Quantity(1.0 / other, self)
        if isinstance(other, PlainUnit):
            return self.__class__(self._units / other._units, self._REGISTRY)
        if hasattr(other, "_units"):
            return self._REGISTRY.Quantity(
                1.0 / other.magnitude, self._units / other._units
            )
        return NotImplemented

    def __rtruediv__(self, other):
        if isinstance(other, Number):
            return self._REGISTRY.Quantity(other, self._units**-1)
        return NotImplemented

    def __pow__(self, other):
        if isinstance(other, Number):
            return self.__class__(self._units**other, self._REGISTRY)
        return NotImplemented

    @property
    def dimensionality(self) -> UnitsContainer:
        """Return the dimensionality of this unit."""
        return self._REGISTRY.get_dimensionality(self._units)

    def _repr_html_(self):
        return self._REGISTRY.formatter.format_unit(self, "H")

    def _repr_latex_(self):
        return "$" + self._REGISTRY.formatter.format_unit(self, "L") + "$"

    def _repr_pretty_(self, p, cycle):
        if cycle:
            p.text("...")
        else:
            p.text(self._REGISTRY.formatter.format_unit(self, "P"))

    def compatible_units(self, *contexts):
        """Return a set of compatible units."""
        return self._REGISTRY.get_compatible_units(self)

    def is_compatible_with(
        self, other: Union["PlainUnit", str], *contexts
    ) -> bool:
        """Check if this unit is compatible with another."""
        if isinstance(other, str):
            other = self._REGISTRY.parse_units(other)
        return self.dimensionality == other.dimensionality


# For backwards compatibility
Unit = PlainUnit
