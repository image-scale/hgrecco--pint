"""
    pint.formatting
    ~~~~~~~~~~~~~~~

    Unit and quantity formatting.
"""
from __future__ import annotations

import re
from typing import Any, Callable, Dict, Tuple

from .delegates.formatter._spec_helpers import REGISTERED_FORMATTERS


# Format flags
_BASIC_FLAGS = frozenset("~LHPCZsrfgeE#")


def _parse_spec(spec: str) -> str:
    """Parse a format specification.

    Parameters
    ----------
    spec : str
        Format specification string.

    Returns
    -------
    str
        The parsed specification.

    Raises
    ------
    ValueError
        If the specification contains invalid flags.
    """
    if not spec:
        return ""

    # Check for invalid flags
    for char in spec:
        if char.isalpha() and char not in _BASIC_FLAGS:
            if spec.count(char) == 1 and char not in "dDxXoObBeEfFgGn":
                # Check if it's a custom format
                if char not in REGISTERED_FORMATTERS:
                    raise ValueError(f"Unknown format flag: {char}")

    # Check for multiple main format flags
    main_flags = "LHPC"
    count = sum(1 for c in spec if c in main_flags)
    if count > 1:
        raise ValueError(f"Too many format flags in: {spec}")

    return spec


def format_unit(unit: str, spec: str = "") -> str:
    """Format a unit string.

    Parameters
    ----------
    unit : str
        Unit string.
    spec : str
        Format specification.

    Returns
    -------
    str
        Formatted unit string.
    """
    if not unit or unit == "dimensionless":
        if "C" in spec:
            return "dimensionless"
        return "dimensionless"

    spec = _parse_spec(spec)

    # Check for invalid specifications
    if spec and spec[0] not in _BASIC_FLAGS and spec[0] not in REGISTERED_FORMATTERS:
        raise ValueError(f"Unknown format specification: {spec}")

    return unit


def formatter(
    items,
    as_ratio: bool = True,
    single_denominator: bool = False,
    product_fmt: str = " * ",
    division_fmt: str = " / ",
    power_fmt: str = "{} ** {}",
    parentheses_fmt: str = "({0})",
    exp_call: Callable = lambda x, y: f"{x} ** {y}",
    sort: bool = True,
) -> str:
    """Format unit items as a string.

    This is a compatibility wrapper around the delegate formatter.
    """
    from .delegates.formatter._format_helpers import formatter as delegate_formatter

    # Convert items to the format expected by the delegate
    items = list(items)
    num_items = [(k, v) for k, v in items if v > 0]
    den_items = [(k, -v) for k, v in items if v < 0]

    return delegate_formatter(
        num_items,
        den_items,
        as_ratio=as_ratio,
        single_denominator=single_denominator,
        product_fmt=product_fmt,
        division_fmt=division_fmt,
        power_fmt=power_fmt,
        parentheses_fmt=parentheses_fmt,
        exp_call=exp_call,
        sort=sort,
    )


def register_unit_format(name: str):
    """Register a custom unit formatter.

    Parameters
    ----------
    name : str
        The name of the format (used as the format flag).

    Returns
    -------
    Callable
        A decorator that registers the formatter function.
    """
    def decorator(func: Callable) -> Callable:
        REGISTERED_FORMATTERS[name] = func
        return func

    return decorator
