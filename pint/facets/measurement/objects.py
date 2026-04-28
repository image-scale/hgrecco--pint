"""
    pint.facets.measurement.objects
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Measurement class for quantities with uncertainties.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional, Union

if TYPE_CHECKING:
    from ...facets.plain.quantity import PlainQuantity
    from ...registry import UnitRegistry


class Measurement:
    """A quantity with an uncertainty.

    Measurements are used to represent physical quantities with
    associated uncertainties.
    """

    def __init__(
        self,
        value: Union["PlainQuantity", float],
        error: Union["PlainQuantity", float, None] = None,
        units: Optional[str] = None,
    ):
        # Get the application registry
        from ... import get_application_registry

        self._REGISTRY = get_application_registry()
        Quantity = self._REGISTRY.Quantity

        # Handle different input patterns
        if isinstance(value, Quantity) and error is None and units is None:
            # Single quantity with uncertainty already attached
            self._value = value
            self._error = Quantity(0, value._units)
        elif isinstance(value, Quantity) and isinstance(error, Quantity):
            # Two quantities - value and error
            self._value = value
            self._error = error.to(value._units)
        elif units is not None:
            # Three-arg form: value, error, units
            self._value = Quantity(value, units)
            self._error = Quantity(error, units)
        else:
            raise TypeError("Invalid arguments for Measurement")

    @property
    def value(self) -> "PlainQuantity":
        """Return the value of this measurement."""
        return self._value

    @property
    def error(self) -> "PlainQuantity":
        """Return the error/uncertainty of this measurement."""
        return self._error

    @property
    def magnitude(self):
        """Return the magnitude of the value."""
        return self._value.magnitude

    @property
    def units(self):
        """Return the units of this measurement."""
        return self._value.units

    @property
    def dimensionality(self):
        """Return the dimensionality of this measurement."""
        return self._value.dimensionality

    def to(self, units):
        """Convert to different units."""
        new_value = self._value.to(units)
        new_error = self._error.to(units)
        result = Measurement.__new__(Measurement)
        result._REGISTRY = self._REGISTRY
        result._value = new_value
        result._error = new_error
        return result

    def __repr__(self):
        return f"Measurement({self._value!r}, {self._error!r})"

    def __str__(self):
        return f"{self._value} ± {self._error}"

    def __reduce__(self):
        from ... import _unpickle_measurement

        return _unpickle_measurement, (
            self.__class__,
            self._value,
            self._error,
        )
