"""Measurement class — a quantity with associated uncertainty."""

import math
from .quantity import Quantity
from .unit_map import UnitMap


class Measurement:
    """Represents a physical measurement with uncertainty.

    A Measurement combines a central value with an error (uncertainty).
    Uncertainty is propagated through arithmetic operations.
    """

    __slots__ = ("_value", "_error", "_registry")

    def __init__(self, value, error=None, units=None, registry=None):
        if isinstance(value, Measurement):
            self._value = value._value
            self._error = value._error
            self._registry = value._registry
            return

        if isinstance(value, Quantity):
            if registry is None:
                registry = value._registry
            val_q = value
        else:
            if registry is None:
                from .registry import UnitRegistry
                registry = UnitRegistry()
            if units is not None:
                val_q = Quantity(value, units, registry=registry)
            else:
                val_q = Quantity(value, registry=registry)

        self._registry = registry

        if isinstance(error, Quantity):
            err_q = error.to(val_q._units)
        elif error is not None:
            if units is not None:
                err_q = Quantity(abs(error), units, registry=registry)
            else:
                err_q = Quantity(abs(error), val_q._units, registry=registry)
        else:
            err_q = Quantity(0, val_q._units, registry=registry)

        self._value = val_q
        self._error = Quantity(abs(err_q._magnitude), err_q._units, registry=registry)

    @property
    def value(self):
        return self._value

    @property
    def error(self):
        return self._error

    @property
    def magnitude(self):
        return self._value._magnitude

    @property
    def units(self):
        return self._value.units

    @property
    def rel(self):
        if self._value._magnitude == 0:
            return float("inf") if self._error._magnitude != 0 else 0.0
        return abs(self._error._magnitude / self._value._magnitude)

    def to(self, other_units):
        new_val = self._value.to(other_units)
        new_err = self._error.to(other_units)
        result = Measurement.__new__(Measurement)
        result._value = new_val
        result._error = Quantity(abs(new_err._magnitude), new_err._units, registry=self._registry)
        result._registry = self._registry
        return result

    def __add__(self, other):
        if isinstance(other, Measurement):
            new_val = self._value + other._value
            new_err_mag = math.sqrt(self._error._magnitude ** 2 + other._error.to(self._error._units)._magnitude ** 2)
            new_err = Quantity(new_err_mag, new_val._units, registry=self._registry)
            return _make_measurement(new_val, new_err, self._registry)

        if isinstance(other, Quantity):
            new_val = self._value + other
            return _make_measurement(new_val, self._error, self._registry)

        if isinstance(other, (int, float)):
            new_val = self._value + other
            return _make_measurement(new_val, self._error, self._registry)

        return NotImplemented

    def __radd__(self, other):
        return self.__add__(other)

    def __sub__(self, other):
        if isinstance(other, Measurement):
            new_val = self._value - other._value
            new_err_mag = math.sqrt(self._error._magnitude ** 2 + other._error.to(self._error._units)._magnitude ** 2)
            new_err = Quantity(new_err_mag, new_val._units, registry=self._registry)
            return _make_measurement(new_val, new_err, self._registry)

        if isinstance(other, Quantity):
            new_val = self._value - other
            return _make_measurement(new_val, self._error, self._registry)

        if isinstance(other, (int, float)):
            new_val = self._value - other
            return _make_measurement(new_val, self._error, self._registry)

        return NotImplemented

    def __rsub__(self, other):
        if isinstance(other, (int, float, Quantity)):
            result = self.__sub__(other)
            if result is NotImplemented:
                return result
            result._value = -result._value + 2 * other
            return result
        return NotImplemented

    def __mul__(self, other):
        if isinstance(other, Measurement):
            new_val = self._value * other._value
            rel_err = math.sqrt(self.rel ** 2 + other.rel ** 2)
            new_err_mag = abs(new_val._magnitude) * rel_err
            new_err = Quantity(new_err_mag, new_val._units, registry=self._registry)
            return _make_measurement(new_val, new_err, self._registry)

        if isinstance(other, Quantity):
            new_val = self._value * other
            new_err = self._error * abs(other._magnitude)
            return _make_measurement(new_val, Quantity(abs(new_err._magnitude), new_err._units, registry=self._registry), self._registry)

        if isinstance(other, (int, float)):
            new_val = self._value * other
            new_err = Quantity(abs(self._error._magnitude * other), self._error._units, registry=self._registry)
            return _make_measurement(new_val, new_err, self._registry)

        return NotImplemented

    def __rmul__(self, other):
        return self.__mul__(other)

    def __truediv__(self, other):
        if isinstance(other, Measurement):
            new_val = self._value / other._value
            rel_err = math.sqrt(self.rel ** 2 + other.rel ** 2)
            new_err_mag = abs(new_val._magnitude) * rel_err
            new_err = Quantity(new_err_mag, new_val._units, registry=self._registry)
            return _make_measurement(new_val, new_err, self._registry)

        if isinstance(other, Quantity):
            new_val = self._value / other
            new_err = self._error / abs(other._magnitude)
            return _make_measurement(new_val, Quantity(abs(new_err._magnitude), new_err._units, registry=self._registry), self._registry)

        if isinstance(other, (int, float)):
            new_val = self._value / other
            new_err = Quantity(abs(self._error._magnitude / other), self._error._units, registry=self._registry)
            return _make_measurement(new_val, new_err, self._registry)

        return NotImplemented

    def __pow__(self, exponent):
        if isinstance(exponent, (int, float)):
            new_val = self._value ** exponent
            rel_err = abs(exponent) * self.rel
            new_err_mag = abs(new_val._magnitude) * rel_err
            new_err = Quantity(new_err_mag, new_val._units, registry=self._registry)
            return _make_measurement(new_val, new_err, self._registry)
        return NotImplemented

    def __neg__(self):
        return _make_measurement(-self._value, self._error, self._registry)

    def __abs__(self):
        return _make_measurement(abs(self._value), self._error, self._registry)

    def __repr__(self):
        return f"<Measurement({self._value.magnitude}, {self._error.magnitude}, '{self._value._units}')>"

    def __str__(self):
        return f"{self._value.magnitude} +/- {self._error.magnitude} {_units_str(self._value._units)}"

    def __format__(self, spec):
        if not spec:
            return str(self)
        from .formatting import format_unit, split_format_spec
        mag_spec, unit_spec = split_format_spec(spec)
        val_str = format(self._value.magnitude, mag_spec) if mag_spec else str(self._value.magnitude)
        err_str = format(self._error.magnitude, mag_spec) if mag_spec else str(self._error.magnitude)
        unit_str = format_unit(self._value._units, unit_spec, self._registry)
        if unit_str == "dimensionless":
            return f"{val_str} +/- {err_str}"
        return f"{val_str} +/- {err_str} {unit_str}"

    def __eq__(self, other):
        if isinstance(other, Measurement):
            return self._value == other._value and self._error == other._error
        return NotImplemented

    def __hash__(self):
        return hash((self._value, self._error))


def _make_measurement(value, error, registry):
    m = Measurement.__new__(Measurement)
    m._value = value
    m._error = Quantity(abs(error._magnitude), error._units, registry=registry)
    m._registry = registry
    return m


def _units_str(units):
    from .formatting import format_unit
    return format_unit(units, "D")
