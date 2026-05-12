"""Converter classes for converting between unit scales."""
from dataclasses import dataclass


@dataclass(frozen=True)
class ScaleConverter:
    """Converts by multiplying/dividing by a scale factor."""
    factor: float

    @property
    def is_multiplicative(self):
        return True

    @property
    def is_offset(self):
        return False

    def to_reference(self, value):
        return value * self.factor

    def from_reference(self, value):
        return value / self.factor


@dataclass(frozen=True)
class OffsetConverter:
    """Converts by applying scale + offset (e.g. temperature scales).

    to_reference: value_ref = value * factor + offset
    from_reference: value = (value_ref - offset) / factor
    """
    factor: float
    offset: float

    @property
    def is_multiplicative(self):
        return self.offset == 0

    @property
    def is_offset(self):
        return True

    def to_reference(self, value):
        return value * self.factor + self.offset

    def from_reference(self, value):
        return (value - self.offset) / self.factor


@dataclass(frozen=True)
class IdentityConverter:
    """No conversion (base units)."""

    @property
    def is_multiplicative(self):
        return True

    @property
    def is_offset(self):
        return False

    @property
    def factor(self):
        return 1.0

    def to_reference(self, value):
        return value

    def from_reference(self, value):
        return value
