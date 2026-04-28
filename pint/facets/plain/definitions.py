"""
    pint.facets.plain.definitions
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Definition classes for the plain facet.
"""
from __future__ import annotations

from dataclasses import dataclass
from numbers import Number
from typing import Any, Callable, Optional, Tuple, Union

from ...compat import HAS_NUMPY
from ...util import UnitsContainer

if HAS_NUMPY:
    from ...compat import np


@dataclass(frozen=True)
class ScaleConverter:
    """A converter for multiplicative units."""

    scale: float = 1.0

    @property
    def is_multiplicative(self) -> bool:
        return True

    @property
    def is_logarithmic(self) -> bool:
        return False

    def to_reference(self, value, inplace=False):
        if HAS_NUMPY and inplace and isinstance(value, np.ndarray):
            value *= self.scale
            return value
        return value * self.scale

    def from_reference(self, value, inplace=False):
        if HAS_NUMPY and inplace and isinstance(value, np.ndarray):
            value /= self.scale
            return value
        return value / self.scale


@dataclass(frozen=False)
class PrefixDefinition:
    """Definition of a prefix."""

    name: str
    symbol: Optional[str] = None
    aliases: Tuple[str, ...] = ()
    converter: ScaleConverter = None

    def __post_init__(self):
        if self.converter is None:
            self.converter = ScaleConverter(1.0)

    @property
    def is_base(self) -> bool:
        return False

    @classmethod
    def from_string(cls, definition: str) -> "PrefixDefinition":
        """Parse a prefix definition from a string."""
        # e.g., "kilo- = 1e3 = k-"
        parts = definition.split("=")
        parts = [p.strip() for p in parts]

        name = parts[0].rstrip("-").strip()
        scale_str = parts[1].strip()

        # Parse scale
        try:
            if "**" in scale_str:
                base, exp = scale_str.split("**")
                scale = float(base.strip()) ** float(exp.strip())
            elif "^" in scale_str:
                base, exp = scale_str.split("^")
                scale = float(base.strip()) ** float(exp.strip())
            else:
                scale = float(scale_str)
        except ValueError:
            raise ValueError(f"Invalid prefix scale: {scale_str}")

        converter = ScaleConverter(scale)

        # Parse symbol and aliases
        symbol = None
        aliases = []
        for part in parts[2:]:
            part = part.strip().rstrip("-")
            if symbol is None:
                symbol = part
            else:
                aliases.append(part)

        return cls(
            name=name,
            symbol=symbol,
            aliases=tuple(aliases),
            converter=converter,
        )


@dataclass(frozen=False)
class UnitDefinition:
    """Definition of a unit."""

    name: str
    symbol: Optional[str] = None
    aliases: Tuple[str, ...] = ()
    converter: Any = None
    reference: UnitsContainer = None
    is_base: bool = False

    def __post_init__(self):
        if self.converter is None:
            self.converter = ScaleConverter(1.0)
        if self.reference is None:
            self.reference = UnitsContainer()
        if self.symbol is None:
            self.symbol = self.name


@dataclass(frozen=False)
class DimensionDefinition:
    """Definition of a dimension."""

    name: str
    reference: UnitsContainer = None

    def __post_init__(self):
        if self.reference is None:
            self.reference = UnitsContainer()

    @property
    def is_base(self) -> bool:
        return not bool(self.reference)


@dataclass(frozen=False)
class AliasDefinition:
    """Definition of an alias."""

    name: str
    aliases: Tuple[str, ...] = ()
