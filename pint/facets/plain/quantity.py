"""
    pint.facets.plain.quantity
    ~~~~~~~~~~~~~~~~~~~~~~~~~~

    Quantity class for the plain facet.
"""
from __future__ import annotations

import copy
import locale
import logging
import math
import numbers
import operator
import warnings
from fractions import Fraction
from typing import TYPE_CHECKING, Any, Callable, Optional, Tuple, Union

from ...compat import HAS_NUMPY, is_duck_array
from ...errors import (
    DimensionalityError,
    OffsetUnitCalculusError,
    UndefinedBehavior,
)
from ...util import UnitsContainer

if TYPE_CHECKING:
    from .registry import PlainRegistry
    from .unit import PlainUnit

if HAS_NUMPY:
    from ...compat import np


logger = logging.getLogger(__name__)


class PlainQuantity:
    """A quantity with a magnitude and units.

    This class should not be instantiated directly. Use the UnitRegistry
    instead.
    """

    __slots__ = ("_magnitude", "_units", "_REGISTRY")

    def __new__(cls, value, units=None):
        inst = object.__new__(cls)
        return inst

    def __init__(
        self,
        value: Any,
        units: Union[UnitsContainer, str, "PlainUnit", None] = None,
    ):
        # Handle the case where we're passed another quantity
        if isinstance(value, PlainQuantity):
            if units is not None:
                self._magnitude = value.to(units).magnitude
                if isinstance(units, str):
                    self._units = value._REGISTRY.parse_units(units)._units
                elif isinstance(units, UnitsContainer):
                    self._units = units
                else:
                    self._units = units._units
            else:
                self._magnitude = value._magnitude
                self._units = value._units
            self._REGISTRY = value._REGISTRY
            return

        # Handle string parsing
        if isinstance(value, str) and units is None:
            # Parse the string as "value units"
            parsed = self._REGISTRY.parse_expression(value)
            self._magnitude = parsed.magnitude
            self._units = parsed._units
            return

        self._magnitude = value

        if units is None:
            self._units = UnitsContainer()
        elif isinstance(units, UnitsContainer):
            self._units = units
        elif isinstance(units, str):
            self._units = self._REGISTRY.parse_units(units)._units
        elif hasattr(units, "_units"):
            # It's a Unit
            self._units = units._units
            if hasattr(units, "magnitude"):
                # It's actually a Quantity being used as units
                if units.magnitude != 1:
                    logger.warning(
                        "Creating a Quantity with a Quantity as units. "
                        "The magnitude of the units Quantity will be dropped."
                    )
        else:
            raise TypeError(f"units must be a string, UnitsContainer, or Unit, not {type(units)}")

    def __reduce__(self):
        from ... import _unpickle_quantity

        return _unpickle_quantity, (
            self.__class__,
            self._magnitude,
            self._units,
        )

    def __copy__(self):
        ret = self.__class__.__new__(self.__class__)
        ret._magnitude = self._magnitude
        ret._units = self._units
        ret._REGISTRY = self._REGISTRY
        return ret

    def __deepcopy__(self, memo):
        ret = self.__class__.__new__(self.__class__)
        ret._magnitude = copy.deepcopy(self._magnitude, memo)
        ret._units = copy.deepcopy(self._units, memo)
        ret._REGISTRY = self._REGISTRY
        return ret

    def __str__(self):
        return self._REGISTRY.formatter.format_quantity(self)

    def __repr__(self):
        return f'Quantity({self._magnitude!r}, "{self._units}")'

    def __format__(self, spec):
        return self._REGISTRY.formatter.format_quantity(self, spec)

    def __hash__(self):
        # Convert to base units for consistent hashing
        try:
            base = self.to_base_units()
            # Round to avoid floating point issues
            if isinstance(base._magnitude, float):
                m = round(base._magnitude, 10)
            else:
                m = base._magnitude
            if base.dimensionless:
                return hash(m)
            return hash((m, base._units))
        except Exception:
            return hash((self._magnitude, self._units))

    @property
    def magnitude(self) -> Any:
        """The numerical value of this quantity."""
        return self._magnitude

    @property
    def m(self) -> Any:
        """Shorthand for magnitude."""
        return self._magnitude

    @property
    def units(self) -> "PlainUnit":
        """The units of this quantity."""
        return self._REGISTRY.Unit(self._units)

    @property
    def u(self) -> "PlainUnit":
        """Shorthand for units."""
        return self.units

    @property
    def dimensionality(self) -> UnitsContainer:
        """The dimensionality of this quantity."""
        return self._REGISTRY.get_dimensionality(self._units)

    @property
    def dimensionless(self) -> bool:
        """Check if this quantity is dimensionless."""
        return not self.dimensionality

    def __bool__(self):
        if self._is_multiplicative():
            return bool(self._magnitude)
        else:
            raise ValueError(
                "Cannot determine truthiness of quantities with offset units"
            )

    def _is_multiplicative(self) -> bool:
        """Check if all units are multiplicative."""
        return self._REGISTRY._is_multiplicative(self._units)

    def __eq__(self, other):
        if isinstance(other, PlainQuantity):
            if self._units == other._units:
                return self._magnitude == other._magnitude
            try:
                if self.dimensionality != other.dimensionality:
                    return False
                return self.to(other._units)._magnitude == other._magnitude
            except DimensionalityError:
                return False
        if self.dimensionless:
            return self.to("")._magnitude == other
        return NotImplemented

    def __ne__(self, other):
        result = self.__eq__(other)
        if result is NotImplemented:
            return result
        return not result

    def __lt__(self, other):
        if isinstance(other, PlainQuantity):
            return self._magnitude < other.to(self._units)._magnitude
        if self.dimensionless:
            return self.to("")._magnitude < other
        raise DimensionalityError(self._units, "dimensionless")

    def __le__(self, other):
        if isinstance(other, PlainQuantity):
            return self._magnitude <= other.to(self._units)._magnitude
        if self.dimensionless:
            return self.to("")._magnitude <= other
        raise DimensionalityError(self._units, "dimensionless")

    def __gt__(self, other):
        if isinstance(other, PlainQuantity):
            return self._magnitude > other.to(self._units)._magnitude
        if self.dimensionless:
            return self.to("")._magnitude > other
        raise DimensionalityError(self._units, "dimensionless")

    def __ge__(self, other):
        if isinstance(other, PlainQuantity):
            return self._magnitude >= other.to(self._units)._magnitude
        if self.dimensionless:
            return self.to("")._magnitude >= other
        raise DimensionalityError(self._units, "dimensionless")

    def __add__(self, other):
        if isinstance(other, PlainQuantity):
            return self.__class__(
                self._magnitude + other.to(self._units)._magnitude,
                self._units,
            )
        if self.dimensionless:
            return self.__class__(self.to("")._magnitude + other, "")
        return NotImplemented

    def __radd__(self, other):
        return self.__add__(other)

    def __iadd__(self, other):
        return self.__add__(other)

    def __sub__(self, other):
        if isinstance(other, PlainQuantity):
            return self.__class__(
                self._magnitude - other.to(self._units)._magnitude,
                self._units,
            )
        if self.dimensionless:
            return self.__class__(self.to("")._magnitude - other, "")
        return NotImplemented

    def __rsub__(self, other):
        if isinstance(other, PlainQuantity):
            return other.__sub__(self)
        if self.dimensionless:
            return self.__class__(other - self.to("")._magnitude, "")
        return NotImplemented

    def __isub__(self, other):
        return self.__sub__(other)

    def __mul__(self, other):
        if isinstance(other, PlainQuantity):
            return self.__class__(
                self._magnitude * other._magnitude,
                self._units * other._units,
            )
        if isinstance(other, numbers.Number):
            return self.__class__(self._magnitude * other, self._units)
        if HAS_NUMPY and isinstance(other, np.ndarray):
            return self.__class__(self._magnitude * other, self._units)
        return NotImplemented

    def __rmul__(self, other):
        return self.__mul__(other)

    def __imul__(self, other):
        return self.__mul__(other)

    def __truediv__(self, other):
        if isinstance(other, PlainQuantity):
            return self.__class__(
                self._magnitude / other._magnitude,
                self._units / other._units,
            )
        if isinstance(other, numbers.Number):
            return self.__class__(self._magnitude / other, self._units)
        return NotImplemented

    def __rtruediv__(self, other):
        if isinstance(other, numbers.Number):
            return self.__class__(
                other / self._magnitude,
                self._units**-1,
            )
        return NotImplemented

    def __itruediv__(self, other):
        return self.__truediv__(other)

    def __floordiv__(self, other):
        if isinstance(other, PlainQuantity):
            return self.__class__(
                self._magnitude // other._magnitude,
                self._units / other._units,
            )
        if isinstance(other, numbers.Number):
            return self.__class__(self._magnitude // other, self._units)
        return NotImplemented

    def __rfloordiv__(self, other):
        if isinstance(other, numbers.Number):
            return self.__class__(
                other // self._magnitude,
                self._units**-1,
            )
        return NotImplemented

    def __mod__(self, other):
        if isinstance(other, PlainQuantity):
            return self.__class__(
                self._magnitude % other.to(self._units)._magnitude,
                self._units,
            )
        if isinstance(other, numbers.Number):
            return self.__class__(self._magnitude % other, self._units)
        return NotImplemented

    def __rmod__(self, other):
        if isinstance(other, numbers.Number):
            return self.__class__(
                other % self.to("")._magnitude,
                "",
            )
        return NotImplemented

    def __divmod__(self, other):
        return (self // other, self % other)

    def __pow__(self, other):
        if isinstance(other, numbers.Number):
            return self.__class__(
                self._magnitude**other,
                self._units**other,
            )
        return NotImplemented

    def __rpow__(self, other):
        if self.dimensionless:
            return other ** self.to("")._magnitude
        raise DimensionalityError(self._units, "dimensionless")

    def __neg__(self):
        return self.__class__(-self._magnitude, self._units)

    def __pos__(self):
        return self.__class__(+self._magnitude, self._units)

    def __abs__(self):
        return self.__class__(abs(self._magnitude), self._units)

    def __round__(self, ndigits=None):
        return self.__class__(round(self._magnitude, ndigits), self._units)

    def __int__(self):
        if self.dimensionless:
            return int(self.to("")._magnitude)
        raise DimensionalityError(self._units, "dimensionless")

    def __float__(self):
        if self.dimensionless:
            return float(self.to("")._magnitude)
        raise DimensionalityError(self._units, "dimensionless")

    def __complex__(self):
        if self.dimensionless:
            return complex(self.to("")._magnitude)
        raise DimensionalityError(self._units, "dimensionless")

    def to(self, other=None, *contexts, **ctx_kwargs):
        """Convert to different units."""
        if other is None:
            return self
        return self._REGISTRY.convert(self, other)

    def ito(self, other=None, *contexts, **ctx_kwargs):
        """Inplace convert to different units."""
        result = self.to(other, *contexts, **ctx_kwargs)
        self._magnitude = result._magnitude
        self._units = result._units
        return self

    def to_base_units(self):
        """Convert to base units."""
        return self._REGISTRY.convert_to_base_units(self)

    def ito_base_units(self):
        """Inplace convert to base units."""
        result = self.to_base_units()
        self._magnitude = result._magnitude
        self._units = result._units
        return self

    def to_root_units(self):
        """Convert to root units."""
        return self._REGISTRY.convert_to_root_units(self)

    def ito_root_units(self):
        """Inplace convert to root units."""
        result = self.to_root_units()
        self._magnitude = result._magnitude
        self._units = result._units
        return self

    def to_reduced_units(self):
        """Convert to reduced units."""
        return self._REGISTRY.convert_to_reduced_units(self)

    def ito_reduced_units(self):
        """Inplace convert to reduced units."""
        result = self.to_reduced_units()
        self._magnitude = result._magnitude
        self._units = result._units
        return self

    def to_compact(self, unit=None):
        """Convert to compact units."""
        return self._REGISTRY.to_compact(self, unit)

    def _repr_html_(self):
        return self._REGISTRY.formatter.format_quantity(self, "H")

    def _repr_latex_(self):
        return "$" + self._REGISTRY.formatter.format_quantity(self, "L") + "$"

    def _repr_pretty_(self, p, cycle):
        if cycle:
            p.text("...")
        else:
            p.text(self._REGISTRY.formatter.format_quantity(self, "P"))


# For backwards compatibility
Quantity = PlainQuantity
