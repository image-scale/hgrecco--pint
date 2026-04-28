"""
    pint.delegates.formatter._compound_unit_helpers
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Helpers for formatting compound units.
"""
from __future__ import annotations


def sort_by_dimensionality(items):
    """Sort items by dimensionality for consistent output."""
    return sorted(items, key=lambda x: x[0])
