"""
    pint.converters
    ~~~~~~~~~~~~~~~

    Base converter classes.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Converter:
    """Base class for unit converters."""

    @property
    def is_multiplicative(self) -> bool:
        return True

    @property
    def is_logarithmic(self) -> bool:
        return False

    def to_reference(self, value, inplace=False):
        return value

    def from_reference(self, value, inplace=False):
        return value

    @classmethod
    def from_arguments(
        cls, scale=1, offset=None, logbase=None, logfactor=None
    ) -> "Converter":
        """Create a converter from arguments."""
        from .facets.plain import ScaleConverter
        from .facets.nonmultiplicative.definitions import (
            OffsetConverter,
            LogarithmicConverter,
        )

        if logbase is not None and logfactor is not None:
            return LogarithmicConverter(scale, logbase, logfactor)
        if offset is not None and offset != 0:
            return OffsetConverter(scale, offset)
        return ScaleConverter(scale)
