"""Unit class — represents a unit without magnitude."""

from .unit_map import UnitMap


class Unit:
    """Represents a physical unit (no magnitude)."""

    __slots__ = ("_unit_map", "_registry")

    def __init__(self, units, registry=None):
        if isinstance(units, Unit):
            self._unit_map = units._unit_map
            self._registry = units._registry if registry is None else registry
            return

        if registry is None:
            from .registry import UnitRegistry
            registry = UnitRegistry()
        self._registry = registry

        if isinstance(units, str):
            self._unit_map = registry.parse_unit_string(units)
        elif isinstance(units, UnitMap):
            self._unit_map = units
        elif isinstance(units, dict):
            self._unit_map = UnitMap(units)
        else:
            self._unit_map = registry.parse_unit_string(str(units))

    @property
    def unit_map(self):
        return self._unit_map

    @property
    def dimensionality(self):
        return self._registry.get_dimensionality(self._unit_map)

    @property
    def dimensionless(self):
        return not bool(self.dimensionality)

    def __mul__(self, other):
        if isinstance(other, Unit):
            return Unit(self._unit_map * other._unit_map, registry=self._registry)
        if isinstance(other, (int, float)):
            from .quantity import Quantity
            return Quantity(other, self._unit_map, registry=self._registry)
        from .quantity import Quantity
        if isinstance(other, Quantity):
            return Quantity(
                other._magnitude,
                self._unit_map * other._units,
                registry=self._registry,
            )
        return NotImplemented

    def __rmul__(self, other):
        if isinstance(other, (int, float)):
            from .quantity import Quantity
            return Quantity(other, self._unit_map, registry=self._registry)
        return NotImplemented

    def __truediv__(self, other):
        if isinstance(other, Unit):
            return Unit(self._unit_map / other._unit_map, registry=self._registry)
        return NotImplemented

    def __rtruediv__(self, other):
        if isinstance(other, (int, float)):
            from .quantity import Quantity
            return Quantity(other, self._unit_map ** -1, registry=self._registry)
        return NotImplemented

    def __pow__(self, exponent):
        if isinstance(exponent, (int, float)):
            return Unit(self._unit_map ** exponent, registry=self._registry)
        return NotImplemented

    def __eq__(self, other):
        if isinstance(other, Unit):
            return self._unit_map == other._unit_map
        if isinstance(other, UnitMap):
            return self._unit_map == other
        if isinstance(other, str):
            try:
                other_map = self._registry.parse_unit_string(other)
                return self._unit_map == other_map
            except Exception:
                return False
        return NotImplemented

    def __ne__(self, other):
        result = self.__eq__(other)
        if result is NotImplemented:
            return result
        return not result

    def __hash__(self):
        return hash(self._unit_map)

    def __repr__(self):
        return f"<Unit('{self._unit_map}')>"

    def __str__(self):
        from .quantity import _format_units
        return _format_units(self._unit_map)

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
