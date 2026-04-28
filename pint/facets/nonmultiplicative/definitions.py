"""
    pint.facets.nonmultiplicative.definitions
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Converter classes for non-multiplicative units.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from ...compat import HAS_NUMPY

if HAS_NUMPY:
    from ...compat import np


@dataclass(frozen=True)
class OffsetConverter:
    """A converter for offset units (like Celsius)."""

    scale: float = 1.0
    offset: float = 0.0

    @property
    def is_multiplicative(self) -> bool:
        return False

    @property
    def is_logarithmic(self) -> bool:
        return False

    def to_reference(self, value, inplace=False):
        if HAS_NUMPY and inplace and isinstance(value, np.ndarray):
            value *= self.scale
            value += self.offset
            return value
        return value * self.scale + self.offset

    def from_reference(self, value, inplace=False):
        if HAS_NUMPY and inplace and isinstance(value, np.ndarray):
            value -= self.offset
            value /= self.scale
            return value
        return (value - self.offset) / self.scale


@dataclass(frozen=True)
class LogarithmicConverter:
    """A converter for logarithmic units (like decibels)."""

    scale: float = 1.0
    logbase: float = 10.0
    logfactor: float = 1.0

    @property
    def is_multiplicative(self) -> bool:
        return False

    @property
    def is_logarithmic(self) -> bool:
        return True

    def to_reference(self, value, inplace=False):
        """Convert from logarithmic to linear scale."""
        if HAS_NUMPY and isinstance(value, np.ndarray):
            if inplace:
                value[:] = self.scale * np.power(self.logbase, value / self.logfactor)
                return value
            return self.scale * np.power(self.logbase, value / self.logfactor)
        return self.scale * (self.logbase ** (value / self.logfactor))

    def from_reference(self, value, inplace=False):
        """Convert from linear to logarithmic scale."""
        if HAS_NUMPY and isinstance(value, np.ndarray):
            if inplace:
                value[:] = self.logfactor * np.log(value / self.scale) / np.log(self.logbase)
                return value
            return self.logfactor * np.log(value / self.scale) / np.log(self.logbase)
        return self.logfactor * math.log(value / self.scale) / math.log(self.logbase)
