from collections.abc import Mapping
import numbers


class UnitMap(Mapping):
    """Immutable mapping from unit names to their exponents.

    For example, m/s^2 is represented as {"meter": 1, "second": -2}.
    """

    __slots__ = ("_data", "_hash")

    def __init__(self, *args, **kwargs):
        if args and isinstance(args[0], UnitMap):
            self._data = dict(args[0]._data)
        elif args and isinstance(args[0], dict):
            self._data = {}
            for k, v in args[0].items():
                if not isinstance(k, str):
                    raise TypeError(f"Unit name must be a string, got {type(k)}")
                if v != 0:
                    self._data[k] = int(v) if isinstance(v, numbers.Integral) else float(v)
        else:
            raw = dict(*args, **kwargs)
            self._data = {}
            for k, v in raw.items():
                if not isinstance(k, str):
                    raise TypeError(f"Unit name must be a string, got {type(k)}")
                if v != 0:
                    self._data[k] = int(v) if isinstance(v, numbers.Integral) else float(v)
        self._hash = None

    def __getitem__(self, key):
        return self._data.get(key, 0)

    def __iter__(self):
        return iter(self._data)

    def __len__(self):
        return len(self._data)

    def __contains__(self, key):
        return key in self._data

    def __bool__(self):
        return bool(self._data)

    def __mul__(self, other):
        if isinstance(other, UnitMap):
            result = dict(self._data)
            for key, val in other._data.items():
                new_val = result.get(key, 0) + val
                if new_val == 0:
                    result.pop(key, None)
                else:
                    result[key] = new_val
            return UnitMap(result)
        if isinstance(other, (int, float)):
            return self.__pow__(other)
        return NotImplemented

    def __rmul__(self, other):
        return self.__mul__(other)

    def __truediv__(self, other):
        if isinstance(other, UnitMap):
            result = dict(self._data)
            for key, val in other._data.items():
                new_val = result.get(key, 0) - val
                if new_val == 0:
                    result.pop(key, None)
                else:
                    result[key] = new_val
            return UnitMap(result)
        return NotImplemented

    def __pow__(self, exponent):
        if not isinstance(exponent, (int, float)):
            return NotImplemented
        if exponent == 0:
            return UnitMap({})
        result = {}
        for key, val in self._data.items():
            new_val = val * exponent
            if new_val != 0:
                result[key] = int(new_val) if new_val == int(new_val) else new_val
        return UnitMap(result)

    def __eq__(self, other):
        if isinstance(other, UnitMap):
            return self._data == other._data
        if isinstance(other, dict):
            cleaned = {k: v for k, v in other.items() if v != 0}
            return self._data == cleaned
        return NotImplemented

    def __hash__(self):
        if self._hash is None:
            self._hash = hash(frozenset(self._data.items()))
        return self._hash

    def __repr__(self):
        return f"UnitMap({self._data!r})"

    def __str__(self):
        if not self._data:
            return "dimensionless"
        parts = []
        for name, exp in sorted(self._data.items()):
            if exp == 1:
                parts.append(name)
            else:
                parts.append(f"{name} ** {exp}")
        return " * ".join(parts)

    def copy(self):
        return UnitMap(dict(self._data))

    def renamed(self, old_key, new_key):
        if old_key not in self._data:
            return self.copy()
        result = dict(self._data)
        result[new_key] = result.pop(old_key)
        return UnitMap(result)
