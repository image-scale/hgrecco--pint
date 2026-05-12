"""Quantity class — a numeric value with units."""

import math
import operator
from .unit_map import UnitMap
from .errors import IncompatibleDimensionError, UnitNotFoundError


class Quantity:
    """Represents a physical quantity: a numeric magnitude with associated units."""

    __slots__ = ("_magnitude", "_units", "_registry", "_dimensionality")

    def __init__(self, magnitude, units=None, registry=None):
        if isinstance(magnitude, Quantity):
            if units is None:
                self._magnitude = magnitude._magnitude
                self._units = magnitude._units
                self._registry = magnitude._registry if registry is None else registry
                self._dimensionality = None
                return
            else:
                self._registry = magnitude._registry if registry is None else registry
                if isinstance(units, str):
                    units = self._registry.parse_unit_string(units)
                elif isinstance(units, UnitMap):
                    pass
                else:
                    units = UnitMap(units) if isinstance(units, dict) else self._registry.parse_unit_string(str(units))

                if magnitude._units == units:
                    self._magnitude = magnitude._magnitude
                else:
                    self._magnitude = self._registry.convert(
                        magnitude._magnitude, magnitude._units, units
                    )
                self._units = units
                self._dimensionality = None
                return

        if registry is None:
            from .registry import UnitRegistry
            registry = UnitRegistry()
        self._registry = registry

        if isinstance(magnitude, str):
            parsed = registry.parse_expression(magnitude)
            self._magnitude = parsed._magnitude
            self._units = parsed._units
            self._dimensionality = None
            return

        self._magnitude = magnitude

        if units is None:
            self._units = UnitMap({})
        elif isinstance(units, str):
            self._units = registry.parse_unit_string(units)
        elif isinstance(units, UnitMap):
            self._units = units
        elif isinstance(units, dict):
            self._units = UnitMap(units)
        else:
            from .unit import Unit
            if isinstance(units, Unit):
                self._units = units.unit_map
            else:
                self._units = registry.parse_unit_string(str(units))

        self._dimensionality = None

    @property
    def magnitude(self):
        return self._magnitude

    @property
    def m(self):
        return self._magnitude

    @property
    def units(self):
        from .unit import Unit
        return Unit(self._units, registry=self._registry)

    @property
    def u(self):
        return self.units

    @property
    def unit_map(self):
        return self._units

    @property
    def dimensionality(self):
        if self._dimensionality is None:
            self._dimensionality = self._registry.get_dimensionality(self._units)
        return self._dimensionality

    @property
    def dimensionless(self):
        return not bool(self.dimensionality)

    def to(self, other_units):
        if isinstance(other_units, str):
            target = self._registry.parse_unit_string(other_units)
        elif isinstance(other_units, UnitMap):
            target = other_units
        else:
            from .unit import Unit
            if isinstance(other_units, Unit):
                target = other_units.unit_map
            else:
                target = self._registry.parse_unit_string(str(other_units))

        new_mag = self._registry.convert(self._magnitude, self._units, target)
        return Quantity(new_mag, target, registry=self._registry)

    def ito(self, other_units):
        result = self.to(other_units)
        object.__setattr__(self, '_magnitude', result._magnitude)
        object.__setattr__(self, '_units', result._units)
        object.__setattr__(self, '_dimensionality', None)
        return None

    def to_base_units(self):
        scale, base_units = self._registry.get_root_units(self._units)
        return Quantity(self._magnitude * scale, base_units, registry=self._registry)

    def to_reduced_units(self):
        return self.to_base_units()

    def is_compatible_with(self, other):
        if isinstance(other, Quantity):
            return self.dimensionality == other.dimensionality
        if isinstance(other, str):
            try:
                other_dim = self._registry.get_dimensionality(other)
                return self.dimensionality == other_dim
            except Exception:
                return False
        from .unit import Unit
        if isinstance(other, Unit):
            return self.dimensionality == other.dimensionality
        return False

    def to_compact(self, unit=None):
        if unit is not None:
            return self.to(unit)

        if not self._units._data:
            return Quantity(self._magnitude, self._units, registry=self._registry)

        if len(self._units._data) != 1:
            return Quantity(self._magnitude, self._units, registry=self._registry)

        unit_name = list(self._units._data.keys())[0]
        unit_exp = list(self._units._data.values())[0]
        if unit_exp != 1:
            return Quantity(self._magnitude, self._units, registry=self._registry)

        base_mag = abs(self._magnitude)
        if base_mag == 0:
            return Quantity(self._magnitude, self._units, registry=self._registry)

        best_name = unit_name
        best_mag = self._magnitude
        best_score = abs(math.log10(base_mag)) if base_mag > 0 else 0

        base_unit = self._find_base_unit_name(unit_name)
        if base_unit is None:
            base_unit = unit_name

        _DECIMAL_PREFIXES = {
            "quecto", "ronto", "yocto", "zepto", "atto", "femto", "pico",
            "nano", "micro", "milli", "centi", "deci",
            "deca", "hecto", "kilo", "mega", "giga", "tera",
            "peta", "exa", "zetta", "yotta", "ronna", "quetta",
        }

        prefix_factors = sorted(
            [(pn, pd.factor) for pn, pd in self._registry._prefixes.items()
             if pn in _DECIMAL_PREFIXES],
            key=lambda x: x[1]
        )

        for pname, pfactor in prefix_factors:
            prefixed = pname + base_unit
            try:
                conv = self._registry.get_conversion_factor(
                    self._units, UnitMap({prefixed: 1})
                )
                new_mag = abs(self._magnitude * conv)
                if new_mag == 0:
                    continue
                score = abs(math.log10(new_mag))
                if score < best_score:
                    best_score = score
                    best_name = prefixed
                    best_mag = self._magnitude * conv
            except Exception:
                continue

        if best_name == unit_name:
            return Quantity(self._magnitude, self._units, registry=self._registry)

        return self.to(best_name)

    def _find_base_unit_name(self, unit_name):
        if unit_name in self._registry._units:
            udef = self._registry._units[unit_name]
            if udef.is_base:
                return unit_name
        for pname in self._registry._prefixes:
            if unit_name.startswith(pname) and len(unit_name) > len(pname):
                remainder = unit_name[len(pname):]
                if remainder in self._registry._units:
                    return remainder
        return None

    def _check_same_registry(self, other):
        if isinstance(other, Quantity):
            return other._registry is self._registry

    def __add__(self, other):
        if isinstance(other, Quantity):
            if not self._units:
                return Quantity(
                    self._magnitude + other._magnitude,
                    other._units,
                    registry=self._registry,
                )
            if not other._units:
                return Quantity(
                    self._magnitude + other._magnitude,
                    self._units,
                    registry=self._registry,
                )
            other_converted = other.to(self._units)
            return Quantity(
                self._magnitude + other_converted._magnitude,
                self._units,
                registry=self._registry,
            )
        if isinstance(other, (int, float)):
            if not self._units or other == 0:
                return Quantity(self._magnitude + other, self._units, registry=self._registry)
            if self.dimensionless:
                return Quantity(self._magnitude + other, self._units, registry=self._registry)
            raise IncompatibleDimensionError(
                str(self._units), "dimensionless",
                str(self.dimensionality), "dimensionless"
            )
        return NotImplemented

    def __radd__(self, other):
        if isinstance(other, (int, float)):
            return self.__add__(other)
        return NotImplemented

    def __sub__(self, other):
        if isinstance(other, Quantity):
            if not self._units:
                return Quantity(
                    self._magnitude - other._magnitude,
                    other._units,
                    registry=self._registry,
                )
            if not other._units:
                return Quantity(
                    self._magnitude - other._magnitude,
                    self._units,
                    registry=self._registry,
                )
            other_converted = other.to(self._units)
            return Quantity(
                self._magnitude - other_converted._magnitude,
                self._units,
                registry=self._registry,
            )
        if isinstance(other, (int, float)):
            if not self._units or other == 0:
                return Quantity(self._magnitude - other, self._units, registry=self._registry)
            if self.dimensionless:
                return Quantity(self._magnitude - other, self._units, registry=self._registry)
            raise IncompatibleDimensionError(
                str(self._units), "dimensionless",
                str(self.dimensionality), "dimensionless"
            )
        return NotImplemented

    def __rsub__(self, other):
        if isinstance(other, (int, float)):
            return Quantity(-self._magnitude + other, self._units, registry=self._registry)
        return NotImplemented

    def __mul__(self, other):
        if isinstance(other, Quantity):
            new_mag = self._magnitude * other._magnitude
            new_units = self._units * other._units
            return Quantity(new_mag, new_units, registry=self._registry)
        if isinstance(other, (int, float)):
            return Quantity(self._magnitude * other, self._units, registry=self._registry)
        from .unit import Unit
        if isinstance(other, Unit):
            new_units = self._units * other.unit_map
            return Quantity(self._magnitude, new_units, registry=self._registry)
        return NotImplemented

    def __rmul__(self, other):
        if isinstance(other, (int, float)):
            return Quantity(other * self._magnitude, self._units, registry=self._registry)
        return NotImplemented

    def __truediv__(self, other):
        if isinstance(other, Quantity):
            new_mag = self._magnitude / other._magnitude
            new_units = self._units / other._units
            return Quantity(new_mag, new_units, registry=self._registry)
        if isinstance(other, (int, float)):
            return Quantity(self._magnitude / other, self._units, registry=self._registry)
        from .unit import Unit
        if isinstance(other, Unit):
            new_units = self._units / other.unit_map
            return Quantity(self._magnitude, new_units, registry=self._registry)
        return NotImplemented

    def __rtruediv__(self, other):
        if isinstance(other, (int, float)):
            new_units = self._units ** -1
            return Quantity(other / self._magnitude, new_units, registry=self._registry)
        return NotImplemented

    def __floordiv__(self, other):
        if isinstance(other, Quantity):
            new_mag = self._magnitude // other._magnitude
            new_units = self._units / other._units
            return Quantity(new_mag, new_units, registry=self._registry)
        if isinstance(other, (int, float)):
            return Quantity(self._magnitude // other, self._units, registry=self._registry)
        return NotImplemented

    def __mod__(self, other):
        if isinstance(other, Quantity):
            other_conv = other.to(self._units)
            return Quantity(
                self._magnitude % other_conv._magnitude,
                self._units,
                registry=self._registry,
            )
        if isinstance(other, (int, float)):
            return Quantity(self._magnitude % other, self._units, registry=self._registry)
        return NotImplemented

    def __pow__(self, exponent):
        if isinstance(exponent, (int, float)):
            new_mag = self._magnitude ** exponent
            new_units = self._units ** exponent
            return Quantity(new_mag, new_units, registry=self._registry)
        if isinstance(exponent, Quantity):
            if exponent.dimensionless:
                exp_val = exponent.to_base_units()._magnitude
                return self.__pow__(exp_val)
        return NotImplemented

    def __neg__(self):
        return Quantity(-self._magnitude, self._units, registry=self._registry)

    def __pos__(self):
        return Quantity(self._magnitude, self._units, registry=self._registry)

    def __abs__(self):
        return Quantity(abs(self._magnitude), self._units, registry=self._registry)

    def __round__(self, ndigits=None):
        return Quantity(round(self._magnitude, ndigits), self._units, registry=self._registry)

    def __eq__(self, other):
        if isinstance(other, Quantity):
            if self._units == other._units:
                return self._magnitude == other._magnitude
            try:
                other_converted = other.to(self._units)
                return math.isclose(
                    self._magnitude, other_converted._magnitude,
                    rel_tol=1e-9, abs_tol=0
                )
            except (IncompatibleDimensionError, UnitNotFoundError):
                return False
        if isinstance(other, (int, float)):
            if self.dimensionless:
                base = self.to_base_units()
                return base._magnitude == other
            if other == 0 and self._magnitude == 0:
                return True
            return False
        return NotImplemented

    def __ne__(self, other):
        result = self.__eq__(other)
        if result is NotImplemented:
            return result
        return not result

    def __lt__(self, other):
        if isinstance(other, Quantity):
            other_converted = other.to(self._units)
            return self._magnitude < other_converted._magnitude
        if isinstance(other, (int, float)):
            if self.dimensionless:
                return self.to_base_units()._magnitude < other
        return NotImplemented

    def __le__(self, other):
        if isinstance(other, Quantity):
            other_converted = other.to(self._units)
            return self._magnitude <= other_converted._magnitude
        if isinstance(other, (int, float)):
            if self.dimensionless:
                return self.to_base_units()._magnitude <= other
        return NotImplemented

    def __gt__(self, other):
        if isinstance(other, Quantity):
            other_converted = other.to(self._units)
            return self._magnitude > other_converted._magnitude
        if isinstance(other, (int, float)):
            if self.dimensionless:
                return self.to_base_units()._magnitude > other
        return NotImplemented

    def __ge__(self, other):
        if isinstance(other, Quantity):
            other_converted = other.to(self._units)
            return self._magnitude >= other_converted._magnitude
        if isinstance(other, (int, float)):
            if self.dimensionless:
                return self.to_base_units()._magnitude >= other
        return NotImplemented

    def __bool__(self):
        return bool(self._magnitude)

    def __float__(self):
        if self.dimensionless:
            return float(self.to_base_units()._magnitude)
        raise IncompatibleDimensionError(
            str(self._units), "dimensionless",
            str(self.dimensionality), "dimensionless"
        )

    def __int__(self):
        if self.dimensionless:
            return int(self.to_base_units()._magnitude)
        raise IncompatibleDimensionError(
            str(self._units), "dimensionless",
            str(self.dimensionality), "dimensionless"
        )

    def __hash__(self):
        base = self.to_base_units()
        if base.dimensionless:
            return hash(base._magnitude)
        return hash((base._magnitude, base._units))

    def __repr__(self):
        return f"<Quantity({self._magnitude}, '{self._units}')>"

    def __str__(self):
        from .formatting import format_quantity
        return format_quantity(self._magnitude, self._units, "", self._registry)

    def __format__(self, spec):
        if not spec:
            return str(self)
        from .formatting import format_quantity
        return format_quantity(self._magnitude, self._units, spec, self._registry)

    @property
    def compatible_units(self):
        dim = self.dimensionality
        result = set()
        for uname in self._registry._units:
            try:
                udim = self._registry.get_dimensionality(UnitMap({uname: 1}))
                if udim == dim:
                    result.add(uname)
            except Exception:
                pass
        return result


def _format_units(units):
    if isinstance(units, UnitMap):
        data = dict(units._data)
    else:
        data = dict(units)
    if not data:
        return "dimensionless"

    pos = [(k, v) for k, v in sorted(data.items()) if v > 0]
    neg = [(k, v) for k, v in sorted(data.items()) if v < 0]

    def _fmt_part(parts):
        result = []
        for name, exp in parts:
            aexp = abs(exp)
            if aexp == 1:
                result.append(name)
            elif aexp == int(aexp):
                result.append(f"{name} ** {int(aexp)}")
            else:
                result.append(f"{name} ** {aexp}")
        return " * ".join(result)

    if pos and neg:
        return _fmt_part(pos) + " / " + _fmt_part([(n, -e) for n, e in neg])
    elif pos:
        return _fmt_part(pos)
    elif neg:
        return "1 / " + _fmt_part([(n, -e) for n, e in neg])
    return "dimensionless"
