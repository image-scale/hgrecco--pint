"""
    pint.util
    ~~~~~~~~~

    Utility functions and classes for Pint.
"""
from __future__ import annotations

import locale
import logging
import math
import operator
import re
import tokenize
from collections import defaultdict
from collections.abc import Callable, Hashable, Iterable, Mapping
from fractions import Fraction
from io import StringIO
from numbers import Number
from typing import Any, Optional, TypeVar, Union

from .compat import HAS_NUMPY

if HAS_NUMPY:
    from .compat import np


logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

T = TypeVar("T")


class UnitsContainer(Mapping[str, Number]):
    """A container for units.

    Behaves like an immutable dict-like object with unit names as keys
    and exponents as values. Supports arithmetic operations.
    """

    __slots__ = ("_d", "_hash")

    def __init__(self, *args, **kwargs):
        if args:
            if len(args) > 1:
                raise TypeError(
                    f"UnitsContainer takes at most 1 positional argument ({len(args)} given)"
                )
            arg = args[0]
            if isinstance(arg, UnitsContainer):
                self._d = dict(arg._d)
            elif isinstance(arg, Mapping):
                self._d = {}
                for k, v in arg.items():
                    if not isinstance(k, str):
                        raise TypeError(f"key must be a str, not {type(k)}")
                    if not isinstance(v, Number):
                        raise TypeError(f"value must be a number, not {type(v)}")
                    if v != 0:
                        self._d[k] = v
            else:
                raise TypeError(f"UnitsContainer argument must be a mapping, not {type(arg)}")
        else:
            self._d = {}

        for k, v in kwargs.items():
            if not isinstance(k, str):
                raise TypeError(f"key must be a str, not {type(k)}")
            if not isinstance(v, Number):
                raise TypeError(f"value must be a number, not {type(v)}")
            if v != 0:
                self._d[k] = v

        self._hash = None

    def __getitem__(self, key: str) -> Number:
        return self._d.get(key, 0)

    def __iter__(self):
        return iter(self._d)

    def __len__(self):
        return len(self._d)

    def __bool__(self):
        return bool(self._d)

    def __hash__(self):
        if self._hash is None:
            self._hash = hash(frozenset(self._d.items()))
        return self._hash

    def __eq__(self, other):
        if isinstance(other, str):
            return self == self._from_string(other)
        if isinstance(other, UnitsContainer):
            return self._d == other._d
        if isinstance(other, Mapping):
            return self._d == {k: v for k, v in other.items() if v != 0}
        return NotImplemented

    def __ne__(self, other):
        result = self.__eq__(other)
        if result is NotImplemented:
            return result
        return not result

    def __repr__(self):
        return f"UnitsContainer({self._d!r})"

    def __str__(self):
        if not self._d:
            return "dimensionless"
        items = []
        for key in sorted(self._d.keys()):
            value = self._d[key]
            if value == 1:
                items.append(key)
            else:
                items.append(f"{key} ** {value}")
        return " * ".join(items)

    @classmethod
    def _from_string(cls, s: str) -> "UnitsContainer":
        """Create UnitsContainer from a string representation."""
        # Simple parser for strings like "meter / second ** 2"
        result = {}
        s = s.strip()
        if not s or s == "dimensionless":
            return cls()

        # Handle division
        parts = s.split("/")
        numerator = parts[0].strip()
        denominators = parts[1:] if len(parts) > 1 else []

        # Parse numerator
        for term in numerator.split("*"):
            term = term.strip()
            if not term:
                continue
            match = re.match(r"(\w+)\s*\*\*\s*(-?\d+\.?\d*)", term)
            if match:
                unit = match.group(1)
                exp = float(match.group(2))
                if exp == int(exp):
                    exp = int(exp)
                result[unit] = result.get(unit, 0) + exp
            else:
                result[term] = result.get(term, 0) + 1

        # Parse denominators
        for denom in denominators:
            denom = denom.strip()
            if not denom:
                continue
            match = re.match(r"(\w+)\s*\*\*\s*(-?\d+\.?\d*)", denom)
            if match:
                unit = match.group(1)
                exp = float(match.group(2))
                if exp == int(exp):
                    exp = int(exp)
                result[unit] = result.get(unit, 0) - exp
            else:
                result[denom] = result.get(denom, 0) - 1

        return cls(result)

    def __mul__(self, other):
        if isinstance(other, UnitsContainer):
            new_d = dict(self._d)
            for k, v in other._d.items():
                new_d[k] = new_d.get(k, 0) + v
                if new_d[k] == 0:
                    del new_d[k]
            return UnitsContainer(new_d)
        if isinstance(other, str):
            return self * self._from_string(other)
        raise TypeError(f"unsupported operand type(s) for *: 'UnitsContainer' and '{type(other).__name__}'")

    def __imul__(self, other):
        return self * other

    def __rmul__(self, other):
        return self * other

    def __truediv__(self, other):
        if isinstance(other, UnitsContainer):
            new_d = dict(self._d)
            for k, v in other._d.items():
                new_d[k] = new_d.get(k, 0) - v
                if new_d[k] == 0:
                    del new_d[k]
            return UnitsContainer(new_d)
        if isinstance(other, str):
            return self / self._from_string(other)
        raise TypeError(f"unsupported operand type(s) for /: 'UnitsContainer' and '{type(other).__name__}'")

    def __itruediv__(self, other):
        return self / other

    def __rtruediv__(self, other):
        if isinstance(other, UnitsContainer):
            return other / self
        if isinstance(other, str):
            return self._from_string(other) / self
        raise TypeError(f"unsupported operand type(s) for /: '{type(other).__name__}' and 'UnitsContainer'")

    def __pow__(self, other):
        if isinstance(other, Number):
            new_d = {k: v * other for k, v in self._d.items()}
            # Clean up zeros
            new_d = {k: v for k, v in new_d.items() if v != 0}
            return UnitsContainer(new_d)
        raise TypeError(f"unsupported operand type(s) for **: 'UnitsContainer' and '{type(other).__name__}'")

    def __ipow__(self, other):
        return self ** other

    def items(self):
        return self._d.items()

    def keys(self):
        return self._d.keys()

    def values(self):
        return self._d.values()

    def copy(self):
        return UnitsContainer(self._d.copy())


class ParserHelper(dict):
    """A helper class for parsing unit expressions.

    Extends dict to store unit exponents and includes a scale factor.
    """

    __slots__ = ("scale",)

    def __init__(self, scale=1, **kwargs):
        super().__init__(**kwargs)
        self.scale = scale

    def __missing__(self, key):
        return 0

    def __repr__(self):
        return f"ParserHelper({self.scale!r}, {dict(self)!r})"

    def __hash__(self):
        return hash((self.scale, frozenset(self.items())))

    def __eq__(self, other):
        if isinstance(other, ParserHelper):
            return self.scale == other.scale and dict.__eq__(self, other)
        if isinstance(other, Number):
            return self.scale == other and len(self) == 0
        if isinstance(other, dict):
            return self.scale == 1 and dict.__eq__(self, other)
        if isinstance(other, str):
            return self == ParserHelper.from_string(other)
        return NotImplemented

    def __ne__(self, other):
        result = self.__eq__(other)
        if result is NotImplemented:
            return result
        return not result

    def copy(self):
        new = ParserHelper(self.scale)
        new.update(self)
        return new

    def __mul__(self, other):
        if isinstance(other, ParserHelper):
            result = self.copy()
            result.scale *= other.scale
            for k, v in other.items():
                result[k] = result.get(k, 0) + v
                if result[k] == 0:
                    del result[k]
            return result
        if isinstance(other, Number):
            result = self.copy()
            result.scale *= other
            return result
        if isinstance(other, str):
            result = self.copy()
            result[other] = result.get(other, 0) + 1
            return result
        return NotImplemented

    def __rmul__(self, other):
        return self.__mul__(other)

    def __imul__(self, other):
        return self.__mul__(other)

    def __truediv__(self, other):
        if isinstance(other, ParserHelper):
            result = self.copy()
            result.scale /= other.scale
            for k, v in other.items():
                result[k] = result.get(k, 0) - v
                if result[k] == 0:
                    del result[k]
            return result
        if isinstance(other, Number):
            result = self.copy()
            result.scale /= other
            return result
        if isinstance(other, str):
            result = self.copy()
            result[other] = result.get(other, 0) - 1
            return result
        return NotImplemented

    def __rtruediv__(self, other):
        if isinstance(other, Number):
            result = ParserHelper(other / self.scale)
            for k, v in self.items():
                result[k] = -v
            return result
        if isinstance(other, str):
            result = ParserHelper(1.0 / self.scale)
            for k, v in self.items():
                result[k] = -v
            result[other] = result.get(other, 0) + 1
            return result
        if isinstance(other, dict):
            result = ParserHelper(1.0 / self.scale)
            for k, v in self.items():
                result[k] = -v
            for k, v in other.items():
                result[k] = result.get(k, 0) + v
            return result
        return NotImplemented

    def __pow__(self, other):
        if isinstance(other, Number):
            result = ParserHelper(self.scale**other)
            for k, v in self.items():
                result[k] = v * other
            return result
        return NotImplemented

    @classmethod
    def from_string(cls, s: str) -> "ParserHelper":
        """Parse a string into a ParserHelper."""
        if not s or s.isspace():
            return cls()

        # Import tokenizer here to avoid circular imports
        from .pint_eval import plain_tokenizer, build_eval_tree

        try:
            tree = build_eval_tree(plain_tokenizer(s))
            result = tree.evaluate(lambda x: cls(**{x: 1}))
            if isinstance(result, cls):
                return result
            if isinstance(result, Number):
                return cls(result)
            return cls()
        except Exception:
            return cls()

    @staticmethod
    def eval_token(token) -> Union[int, float]:
        """Evaluate a token to a number."""
        s = token.string
        if "e" in s.lower():
            return float(s)
        if "." in s:
            return float(s)
        return int(s)


def to_units_container(unit_like, registry=None) -> UnitsContainer:
    """Convert a unit-like object to UnitsContainer."""
    if isinstance(unit_like, UnitsContainer):
        return unit_like
    if isinstance(unit_like, str):
        return UnitsContainer._from_string(unit_like)
    if isinstance(unit_like, dict):
        return UnitsContainer(unit_like)
    # Check for Quantity or Unit objects
    if hasattr(unit_like, "_units"):
        return unit_like._units
    raise TypeError(f"Cannot convert {type(unit_like)} to UnitsContainer")


def string_preprocessor(s: str) -> str:
    """Preprocess a string for unit parsing.

    Handles special cases like:
    - ^ -> **
    - squared/cubed -> **2 / **3
    - sq/square/cubic -> **2 / **3
    - per -> /
    - space multiplication
    """
    # Remove commas from numbers
    s = re.sub(r"(\d),(\d)", r"\1\2", s)

    # Replace ^ with **
    s = re.sub(r"\^", "**", s)

    # Handle squared and cubed
    s = re.sub(r"(\w+)\s+squared", r"\1**2", s)
    s = re.sub(r"(\w+)\s+cubed", r"\1**3", s)

    # Handle sq/square/cubic prefixes
    s = re.sub(r"\bsq\s+(\w+)", r"\1**2", s)
    s = re.sub(r"\bsquare\s+(\w+)", r"\1**2", s)
    s = re.sub(r"\bcubic\s+(\w+)", r"\1**3", s)

    # Handle per
    s = re.sub(r"\bper\b", "/", s)

    # Handle space multiplication
    # A number followed by a letter or open paren
    s = re.sub(r"(\d\.?\d*(?:[eE][+-]?\d+)?)\s+([a-zA-Z(])", r"\1*\2", s)
    s = re.sub(r"(\d\.?\d*(?:[eE][+-]?\d+)?)([a-zA-Z])", r"\1*\2", s)
    # Multiple spaces to single space
    s = re.sub(r"\s+", " ", s)
    # Space between letters (units) becomes multiplication
    s = re.sub(r"([a-zA-Z_]\w*)\s+([a-zA-Z_])", r"\1*\2", s)

    return s


def find_connected_nodes(graph: Mapping[T, set[T]], start: T) -> Optional[set[T]]:
    """Find all nodes connected to start in an undirected graph."""
    if start not in graph:
        return None

    visited = set()
    stack = [start]

    while stack:
        node = stack.pop()
        if node not in visited:
            visited.add(node)
            if node in graph:
                for neighbor in graph[node]:
                    if neighbor not in visited:
                        stack.append(neighbor)

    return visited


def find_shortest_path(graph: Mapping[T, set[T]], start: T, end: T) -> Optional[list[T]]:
    """Find the shortest path between start and end in a graph using BFS."""
    if start == end:
        return [start]

    visited = {start}
    queue = [(start, [start])]

    while queue:
        node, path = queue.pop(0)
        if node in graph:
            for neighbor in graph[node]:
                if neighbor == end:
                    return path + [neighbor]
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))

    return None


def matrix_to_string(
    matrix,
    row_headers: Optional[list[str]] = None,
    col_headers: Optional[list[str]] = None,
    fmtfun: Callable[[Any], str] = str,
) -> str:
    """Convert a matrix to a string representation."""
    result = []

    if col_headers is not None:
        if row_headers is not None:
            header = "\t" + "\t".join(col_headers)
        else:
            header = "\t".join(col_headers)
        result.append(header)

    for i, row in enumerate(matrix):
        row_str = [fmtfun(v) for v in row]
        if row_headers is not None:
            row_str = [row_headers[i]] + row_str
        result.append("\t".join(row_str))

    return "\n".join(result)


def transpose(matrix: list[list[T]]) -> list[list[T]]:
    """Transpose a matrix."""
    if not matrix:
        return []
    return [[row[i] for row in matrix] for i in range(len(matrix[0]))]


def iterable(obj) -> bool:
    """Check if an object is iterable (but not a string)."""
    if isinstance(obj, str):
        return True
    try:
        iter(obj)
        return True
    except TypeError:
        return False


def sized(obj) -> bool:
    """Check if an object is sized (has a length)."""
    if isinstance(obj, str):
        return True
    try:
        len(obj)
        return True
    except TypeError:
        return False


def infer_base_unit(unit_like, registry=None):
    """Infer the base unit for a given unit."""
    # This is a stub - actual implementation needs registry
    raise NotImplementedError("infer_base_unit requires a registry")


def getattr_maybe_raise(obj, name, exc=AttributeError):
    """Get an attribute from an object, raising an exception if it doesn't exist."""
    try:
        return getattr(obj, name)
    except AttributeError:
        raise exc


class SourceIterator:
    """Iterator that tracks position in source."""

    def __init__(self, source):
        self.source = source
        self.pos = 0

    def __iter__(self):
        return self

    def __next__(self):
        if self.pos >= len(self.source):
            raise StopIteration
        item = self.source[self.pos]
        self.pos += 1
        return item
